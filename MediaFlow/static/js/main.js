// Main JavaScript for eBook Library

// Initialize page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeComponents();
    setupEventListeners();
});

// Initialize Bootstrap components and custom features
function initializeComponents() {
    // Initialize all tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize all popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
}

// Setup event listeners
function setupEventListeners() {
    // Form validation
    setupFormValidation();
    
    // Search functionality
    setupSearch();
    
    // File upload validation
    setupFileUpload();
    
    // Confirmation dialogs
    setupConfirmationDialogs();
}

// Form validation
function setupFormValidation() {
    var forms = document.querySelectorAll('.needs-validation');
    
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Password confirmation validation
    var passwordField = document.getElementById('password');
    var confirmPasswordField = document.getElementById('confirm_password');
    
    if (passwordField && confirmPasswordField) {
        function validatePassword() {
            if (passwordField.value !== confirmPasswordField.value) {
                confirmPasswordField.setCustomValidity('Passwords do not match');
            } else {
                confirmPasswordField.setCustomValidity('');
            }
        }
        
        passwordField.addEventListener('input', validatePassword);
        confirmPasswordField.addEventListener('input', validatePassword);
    }
}

// Search functionality
function setupSearch() {
    var searchForm = document.querySelector('form[method="GET"]');
    var searchInput = document.querySelector('input[name="q"]');
    var categorySelect = document.querySelector('select[name="category"]');
    
    if (searchForm && searchInput) {
        // Auto-submit on category change
        if (categorySelect) {
            categorySelect.addEventListener('change', function() {
                searchForm.submit();
            });
        }
        
        // Search on Enter key
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchForm.submit();
            }
        });
    }
}

// File upload validation
function setupFileUpload() {
    var fileInput = document.getElementById('file');
    
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            var file = e.target.files[0];
            if (file) {
                // Check file type
                if (!file.type.includes('pdf')) {
                    showAlert('Only PDF files are allowed.', 'danger');
                    e.target.value = '';
                    return;
                }
                
                // Check file size (16MB limit)
                var maxSize = 16 * 1024 * 1024;
                if (file.size > maxSize) {
                    showAlert('File size exceeds 16MB limit. Please choose a smaller file.', 'danger');
                    e.target.value = '';
                    return;
                }
                
                // Show file info
                var fileInfo = document.getElementById('file-info');
                if (!fileInfo) {
                    fileInfo = document.createElement('div');
                    fileInfo.id = 'file-info';
                    fileInfo.className = 'mt-2 text-muted';
                    fileInput.parentNode.appendChild(fileInfo);
                }
                
                fileInfo.innerHTML = `
                    <i class="fas fa-file-pdf text-danger me-1"></i>
                    ${file.name} (${formatFileSize(file.size)})
                `;
            }
        });
    }
}

// Confirmation dialogs
function setupConfirmationDialogs() {
    var deleteLinks = document.querySelectorAll('a[onclick*="confirm"]');
    
    deleteLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            var message = this.getAttribute('onclick').match(/confirm\('([^']+)'\)/);
            if (message && message[1]) {
                if (!confirm(message[1])) {
                    e.preventDefault();
                    return false;
                }
            }
        });
    });
}

// Utility functions
function showAlert(message, type = 'info') {
    var alertContainer = document.querySelector('.container');
    if (!alertContainer) return;
    
    var alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.role = 'alert';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert after navbar
    var navbar = document.querySelector('.navbar');
    if (navbar && navbar.nextSibling) {
        navbar.parentNode.insertBefore(alert, navbar.nextSibling);
    } else {
        alertContainer.insertBefore(alert, alertContainer.firstChild);
    }
    
    // Auto-hide after 5 seconds
    setTimeout(function() {
        var bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
    }, 5000);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    var k = 1024;
    var sizes = ['Bytes', 'KB', 'MB', 'GB'];
    var i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Loading states for buttons
function setButtonLoading(button, loading = true) {
    if (loading) {
        button.classList.add('loading');
        var originalText = button.innerHTML;
        button.setAttribute('data-original-text', originalText);
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Loading...';
        button.disabled = true;
    } else {
        button.classList.remove('loading');
        var originalText = button.getAttribute('data-original-text');
        if (originalText) {
            button.innerHTML = originalText;
        }
        button.disabled = false;
    }
}

// Form submission with loading state
document.addEventListener('submit', function(e) {
    var form = e.target;
    var submitButton = form.querySelector('button[type="submit"]');
    
    if (submitButton) {
        setButtonLoading(submitButton, true);
        
        // Reset loading state if form validation fails
        setTimeout(function() {
            if (form.classList.contains('was-validated') && !form.checkValidity()) {
                setButtonLoading(submitButton, false);
            }
        }, 100);
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K for search focus
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        var searchInput = document.querySelector('input[name="q"]');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }
});

// Theme toggle (if needed in future)
function toggleTheme() {
    var html = document.documentElement;
    var currentTheme = html.getAttribute('data-bs-theme');
    var newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-bs-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

// Smooth scrolling for anchor links
document.addEventListener('click', function(e) {
    var target = e.target.closest('a[href^="#"]');
    if (target) {
        var href = target.getAttribute('href');
        // Check if href is valid selector (not just '#')
        if (href && href.length > 1) {
            var element = document.querySelector(href);
            if (element) {
                e.preventDefault();
                element.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        }
    }
});

// Table responsive enhancement
function enhanceResponsiveTables() {
    var tables = document.querySelectorAll('.table-responsive table');
    tables.forEach(function(table) {
        if (table.scrollWidth > table.clientWidth) {
            table.parentNode.classList.add('table-scroll-indicator');
        }
    });
}

// Call on window resize
window.addEventListener('resize', enhanceResponsiveTables);
enhanceResponsiveTables();
