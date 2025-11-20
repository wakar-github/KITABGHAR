import os
import hashlib
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, abort
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")

# Configure upload settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_CONTENT_LENGTH = 300 * 1024 * 1024  # 300MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# In-memory data storage
users_db = {}  # {user_id: user_data}
books_db = {}  # {book_id: book_data}
user_counter = 1
book_counter = 1

# User roles
ROLES = {
    'reader': 'Reader',
    'author': 'Author', 
    'admin': 'Admin'
}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    return user_data

def get_user_by_username(username):
    for user in users_db.values():
        if user['username'] == username:
            return user
    return None

def get_user_by_id(user_id):
    return users_db.get(user_id)

def authenticate_user(username, password):
    user = get_user_by_username(username)
    if user and check_password_hash(user['password_hash'], password):
        return user
    return None

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
        'downloads': 0
    }
    books_db[book_id] = book_data
    return book_data

def search_books(query=None, category=None):
    results = []
    for book in books_db.values():
        if query:
            query_lower = query.lower()
            if (query_lower in book['title'].lower() or 
                query_lower in book['author'].lower() or
                query_lower in book['description'].lower()):
                if not category or book['category'] == category:
                    results.append(book)
        elif category:
            if book['category'] == category:
                results.append(book)
        else:
            results.append(book)
    return results

def get_all_categories():
    categories = set()
    for book in books_db.values():
        categories.add(book['category'])
    return sorted(list(categories))

def require_login(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def require_role(required_role):
    def decorator(f):
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            
            user = get_user_by_id(session['user_id'])
            if not user:
                flash('User not found.', 'error')
                return redirect(url_for('login'))
            
            role_hierarchy = {'reader': 1, 'author': 2, 'admin': 3}
            user_level = role_hierarchy.get(user['role'], 0)
            required_level = role_hierarchy.get(required_role, 999)
            
            if user_level < required_level:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

# Create default admin user
if not users_db:
    create_user('admin', 'admin@example.com', 'admin123', 'admin')
    create_user('author1', 'author@example.com', 'author123', 'author')
    create_user('reader1', 'reader@example.com', 'reader123', 'reader')

@app.route('/')
def index():
    user = None
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
    
    # Get recent books (last 6)
    recent_books = sorted(books_db.values(), key=lambda x: x['uploaded_at'], reverse=True)[:6]
    total_books = len(books_db)
    total_users = len(users_db)
    
    return render_template('index.html', user=user, recent_books=recent_books, 
                         total_books=total_books, total_users=total_users)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = authenticate_user(username, password)
        if user:
            session['user_id'] = user['id']
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form.get('role', 'reader')
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        if get_user_by_username(username):
            flash('Username already exists.', 'error')
            return render_template('register.html')
        
        if role not in ROLES:
            role = 'reader'
        
        user = create_user(username, email, password, role)
        session['user_id'] = user['id']
        flash(f'Registration successful! Welcome, {username}!', 'success')
        return redirect(url_for('index'))
    
    return render_template('register.html', roles=ROLES)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/browse')
def browse():
    user = None
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
    
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    view_mode = request.args.get('view', 'grid')
    
    books = search_books(query, category if category else None)
    categories = get_all_categories()
    
    return render_template('browse.html', user=user, books=books, categories=categories,
                         query=query, selected_category=category, view_mode=view_mode)

@app.route('/upload', methods=['GET', 'POST'])
@require_role('author')
def upload():
    user = get_user_by_id(session['user_id'])
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        category = request.form['category']
        description = request.form['description']
        
        if 'file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)
        
        if file and file.filename and allowed_file(file.filename):
            # Generate unique filename
            file_extension = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            try:
                file.save(file_path)
                book = create_book(title, author, category, description, unique_filename, user['id'])
                flash(f'Book "{title}" uploaded successfully!', 'success')
                return redirect(url_for('browse'))
            except Exception as e:
                flash(f'Error uploading file: {str(e)}', 'error')
        else:
            flash('Invalid file type. Only PDF files are allowed.', 'error')
    
    categories = get_all_categories()
    return render_template('upload.html', user=user, categories=categories)

@app.route('/download/<int:book_id>')
@require_login
def download(book_id):
    book = books_db.get(book_id)
    if not book:
        abort(404)
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], book['filename'])
    if not os.path.exists(file_path):
        flash('File not found.', 'error')
        return redirect(url_for('browse'))
    
    # Increment download counter
    book['downloads'] += 1
    
    return send_file(file_path, as_attachment=True, download_name=f"{book['title']}.pdf")

@app.route('/admin')
@require_role('admin')
def admin():
    user = get_user_by_id(session['user_id'])
    all_users = list(users_db.values())
    all_books = list(books_db.values())
    
    # Sort by creation date
    all_users.sort(key=lambda x: x['created_at'], reverse=True)
    all_books.sort(key=lambda x: x['uploaded_at'], reverse=True)
    
    return render_template('admin.html', user=user, all_users=all_users, all_books=all_books)

@app.route('/admin/delete_user/<int:user_id>')
@require_role('admin')
def delete_user(user_id):
    if user_id == session['user_id']:
        flash('You cannot delete your own account.', 'error')
    elif user_id in users_db:
        username = users_db[user_id]['username']
        del users_db[user_id]
        flash(f'User "{username}" deleted successfully.', 'success')
    else:
        flash('User not found.', 'error')
    
    return redirect(url_for('admin'))

@app.route('/admin/delete_book/<int:book_id>')
@require_role('admin')
def delete_book(book_id):
    if book_id in books_db:
        book = books_db[book_id]
        # Delete file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], book['filename'])
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logging.error(f"Error deleting file {file_path}: {e}")
        
        title = book['title']
        del books_db[book_id]
        flash(f'Book "{title}" deleted successfully.', 'success')
    else:
        flash('Book not found.', 'error')
    
    return redirect(url_for('admin'))

@app.route('/profile')
@require_login
def profile():
    user = get_user_by_id(session['user_id'])
    
    # Get user's uploaded books if they are an author
    user_books = []
    if user and user['role'] in ['author', 'admin']:
        user_books = [book for book in books_db.values() if book['uploaded_by'] == user['id']]
        user_books.sort(key=lambda x: x['uploaded_at'], reverse=True)
    
    return render_template('profile.html', user=user, user_books=user_books)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
