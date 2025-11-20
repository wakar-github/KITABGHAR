import os
import json
import uuid
import logging
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, send_from_directory, abort
)

# -------------------------
# CONFIGURATION
# -------------------------
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")

# Upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_CONTENT_LENGTH = 300 * 1024 * 1024  # 300MB max file size

# Use absolute path to avoid relative path issues
app.config['UPLOAD_FOLDER'] = os.path.abspath(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
logger.debug(f"Upload folder set to: {app.config['UPLOAD_FOLDER']}")

# Data persistence
DATA_FILE = 'data_store.json'

# In-memory storage
users_db = {}   # {user_id: user_data}
books_db = {}   # {book_id: book_data}
user_counter = 1
book_counter = 1

ROLES = {
    'reader': 'Reader',
    'author': 'Author',
    'admin': 'Admin'
}

# -------------------------
# HELPER FUNCTIONS
# -------------------------
def _dt_to_iso(v):
    return v.isoformat() if isinstance(v, datetime) else v

def _iso_to_dt(s):
    if isinstance(s, str):
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return s
    return s

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -------------------------
# PERSISTENCE
# -------------------------
def load_data():
    global users_db, books_db, user_counter, book_counter
    if not os.path.exists(DATA_FILE):
        logger.debug("No data file found; starting with defaults.")
        return

    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Load users
        raw_users = data.get('users_db', {})
        users_db = {}
        for k, v in raw_users.items():
            uid = int(k)
            user = v.copy()
            if 'created_at' in user:
                user['created_at'] = _iso_to_dt(user['created_at'])
            users_db[uid] = user

        # Load books
        raw_books = data.get('books_db', {})
        books_db = {}
        for k, v in raw_books.items():
            bid = int(k)
            book = v.copy()
            if 'uploaded_at' in book:
                book['uploaded_at'] = _iso_to_dt(book['uploaded_at'])
            book.setdefault('views', 0)
            books_db[bid] = book

        user_counter = int(data.get('user_counter', max(users_db.keys(), default=0) + 1))
        book_counter = int(data.get('book_counter', max(books_db.keys(), default=0) + 1))
        logger.debug(f"Loaded {len(users_db)} users, {len(books_db)} books.")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")

def save_data():
    try:
        users_serial = {
            str(k): {**v, 'created_at': _dt_to_iso(v.get('created_at'))}
            for k, v in users_db.items()
        }
        books_serial = {
            str(k): {**v, 'uploaded_at': _dt_to_iso(v.get('uploaded_at'))}
            for k, v in books_db.items()
        }
        payload = {
            'users_db': users_serial,
            'books_db': books_serial,
            'user_counter': user_counter,
            'book_counter': book_counter
        }
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
        logger.debug("Saved data to disk.")
    except Exception as e:
        logger.error(f"Failed to save data: {e}")

# -------------------------
# USER MANAGEMENT
# -------------------------
def create_user(username, email, password, role='reader'):
    global user_counter
    user_id = user_counter
    user_counter += 1
    user_data = {
        'id': user_id,
        'username': username,
        'email': email,
        'password_hash': generate_password_hash(password),
        'role': role,
        'created_at': datetime.now()
    }
    users_db[user_id] = user_data
    save_data()
    return user_data

def get_user_by_username(username):
    return next((u for u in users_db.values() if u['username'] == username), None)

def get_user_by_id(user_id):
    try:
        user_id = int(user_id)
    except Exception:
        return None
    return users_db.get(user_id)

def authenticate_user(username, password):
    user = get_user_by_username(username)
    return user if user and check_password_hash(user['password_hash'], password) else None

# -------------------------
# BOOK MANAGEMENT
# -------------------------
def create_book(title, author, category, description, filename, uploaded_by):
    global book_counter
    book_id = book_counter
    book_counter += 1
    book_data = {
        'id': book_id,
        'title': title,
        'author': author,
        'category': category,
        'description': description,
        'filename': filename,
        'uploaded_by': uploaded_by,
        'uploaded_at': datetime.now(),
        'downloads': 0,
        'views': 0
    }
    books_db[book_id] = book_data
    save_data()
    return book_data

def search_books(query=None, category=None):
    results = []
    for book in books_db.values():
        if query:
            q = query.lower()
            if q in book.get('title', '').lower() or q in book.get('author', '').lower() or q in book.get('description', '').lower():
                if not category or book.get('category') == category:
                    results.append(book)
        elif category:
            if book.get('category') == category:
                results.append(book)
        else:
            results.append(book)
    return results

def get_all_categories():
    return sorted(set(b.get('category') for b in books_db.values() if b.get('category')))

# -------------------------
# DECORATORS
# -------------------------
def require_login(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def require_role(required_role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in.', 'warning')
                return redirect(url_for('login'))
            user = get_user_by_id(session['user_id'])
            role_hierarchy = {'reader': 1, 'author': 2, 'admin': 3}
            if role_hierarchy.get(user.get('role'), 0) < role_hierarchy.get(required_role, 999):
                flash('Access denied.', 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return wrapper
    return decorator

# -------------------------
# LOAD INITIAL DATA
# -------------------------
load_data()
if not users_db:
    create_user('admin', 'Suman.m202@gmail.com', 'admin123', 'admin')
    create_user('author1', 'author@example.com', 'author123', 'author')
    create_user('reader1', 'reader@example.com', 'reader123', 'reader')

# -------------------------
# ROUTES
# -------------------------
@app.route('/')
def index():
    user = get_user_by_id(session['user_id']) if 'user_id' in session else None
    recent_books = sorted(books_db.values(), key=lambda x: x.get('uploaded_at', datetime.min), reverse=True)[:6]
    return render_template('index.html', user=user,
                           recent_books=recent_books,
                           total_books=len(books_db),
                           total_users=len(users_db))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = authenticate_user(username, password)
        if user:
            session['user_id'] = user['id']
            flash(f"Welcome back, {user['username']}!", 'success')
            return redirect(url_for('index'))
        flash('Invalid credentials.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        confirm = request.form['confirm_password']
        role = request.form.get('role', 'reader')

        if not username or not password:
            flash('Username and password required.', 'error')
        elif password != confirm:
            flash('Passwords do not match.', 'error')
        elif get_user_by_username(username):
            flash('Username already exists.', 'error')
        else:
            if role not in ROLES:
                role = 'reader'
            user = create_user(username, email, password, role)
            session['user_id'] = user['id']
            flash(f"Welcome, {username}!", 'success')
            return redirect(url_for('index'))
    return render_template('register.html', roles=ROLES)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/browse')
def browse():
    user = get_user_by_id(session['user_id']) if 'user_id' in session else None
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '')
    # read view mode from query string, default to 'grid'
    view_mode = request.args.get('view', 'grid')
    books = search_books(q if q else None, category if category else None)

    # sort books if you want consistent order (optional)
    books = sorted(books, key=lambda x: x.get('uploaded_at', datetime.min), reverse=True)

    return render_template('browse.html', user=user, books=books,
                           categories=get_all_categories(),
                           query=q, selected_category=category,
                           view_mode=view_mode)


@app.route('/upload', methods=['GET', 'POST'])
@require_role('author')
def upload():
    user = get_user_by_id(session['user_id'])
    if request.method == 'POST':
        title = request.form['title'].strip()
        author = request.form['author'].strip()
        category = request.form['category'].strip()
        description = request.form['description'].strip()
        file = request.files.get('file')

        if not file or file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)
        if not allowed_file(file.filename):
            flash('Invalid file type. Only PDFs allowed.', 'error')
            return redirect(request.url)

        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        try:
            file.save(file_path)
            logger.info(f"Saved uploaded file: {file_path}")
            create_book(title, author, category, description, unique_filename, user['id'])
            flash(f'Book "{title}" uploaded successfully!', 'success')
            return redirect(url_for('browse'))
        except Exception as e:
            logger.exception("Error saving uploaded file")
            flash(f"Upload failed: {e}", 'error')

    return render_template('upload.html', user=user, categories=get_all_categories())

# -------------------------
# READ & DOWNLOAD ROUTES (fixed)
# -------------------------
@app.route('/download/<int:book_id>')
@require_login
def download(book_id):
    book = books_db.get(book_id)
    if not book:
        abort(404)
    filename = book.get('filename', '')
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    logger.debug(f"Download path={file_path} exists={os.path.exists(file_path)}")
    if not os.path.exists(file_path):
        flash('File not found on server.', 'error')
        return redirect(url_for('browse'))
    book['downloads'] = book.get('downloads', 0) + 1
    save_data()
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename,
                               as_attachment=True,
                               download_name=f"{book.get('title','book')}.pdf",
                               mimetype='application/pdf')

@app.route('/read/<int:book_id>')
@require_login
def read(book_id):
    book = books_db.get(book_id)
    if not book:
        abort(404)
    filename = book.get('filename', '')
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    logger.debug(f"Read path={file_path} exists={os.path.exists(file_path)}")
    if not os.path.exists(file_path):
        flash('File not found on server.', 'error')
        return redirect(url_for('browse'))
    book['views'] = book.get('views', 0) + 1
    save_data()
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename,
                               as_attachment=False,
                               download_name=f"{book.get('title','book')}.pdf",
                               mimetype='application/pdf')

# -------------------------
# ADMIN & PROFILE
# -------------------------
@app.route('/admin')
@require_role('admin')
def admin():
    user = get_user_by_id(session['user_id'])
    all_users = sorted(users_db.values(), key=lambda x: x.get('created_at', datetime.min), reverse=True)
    all_books = sorted(books_db.values(), key=lambda x: x.get('uploaded_at', datetime.min), reverse=True)
    return render_template('admin.html', user=user, all_users=all_users, all_books=all_books)

@app.route('/admin/delete_user/<int:user_id>')
@require_role('admin')
def delete_user(user_id):
    if user_id == session['user_id']:
        flash("You can't delete your own account.", 'error')
    elif user_id in users_db:
        username = users_db[user_id]['username']
        del users_db[user_id]
        save_data()
        flash(f'User "{username}" deleted.', 'success')
    else:
        flash('User not found.', 'error')
    return redirect(url_for('admin'))

@app.route('/admin/delete_book/<int:book_id>')
@require_role('admin')
def delete_book(book_id):
    if book_id in books_db:
        book = books_db[book_id]
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], book.get('filename', ''))
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Error deleting {file_path}: {e}")
        del books_db[book_id]
        save_data()
        flash(f'Book "{book.get("title")}" deleted.', 'success')
    else:
        flash('Book not found.', 'error')
    return redirect(url_for('admin'))

@app.route('/profile')
@require_login
def profile():
    user = get_user_by_id(session['user_id'])
    user_books = []
    if user and user.get('role') in ['author', 'admin']:
        user_books = [b for b in books_db.values() if b.get('uploaded_by') == user['id']]
        user_books.sort(key=lambda x: x.get('uploaded_at', datetime.min), reverse=True)
    return render_template('profile.html', user=user, user_books=user_books)

# -------------------------
# MAIN
# -------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
