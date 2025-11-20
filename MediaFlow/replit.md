# eBook Library Management System

## Overview

The eBook Library Management System is a Flask-based web application that provides a comprehensive platform for managing digital books. The system supports role-based access control with three user types: readers, authors, and administrators. Users can browse, upload, download, and manage PDF eBooks through an intuitive web interface built with Bootstrap and Font Awesome icons.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 dark theme for responsive UI
- **CSS Framework**: Bootstrap 5 with custom CSS overrides for enhanced styling
- **JavaScript**: Vanilla JavaScript for client-side interactions and form validation
- **Icons**: Font Awesome 6.4.0 for consistent iconography throughout the application

### Backend Architecture
- **Web Framework**: Flask (Python) serving as the main application framework
- **Session Management**: Flask sessions with configurable secret key from environment variables
- **Security**: Werkzeug utilities for password hashing and secure filename handling
- **File Handling**: Werkzeug for secure file uploads with size and type restrictions

### Data Storage Solutions
- **Primary Storage**: In-memory dictionaries for user and book data (users_db, books_db)
- **File Storage**: Local filesystem storage for uploaded PDF files in the 'uploads' directory
- **Session Storage**: Flask built-in session management for user authentication state

### Authentication and Authorization
- **Authentication**: Username/password-based login with Werkzeug password hashing
- **Authorization**: Role-based access control with three distinct roles:
  - Reader: Browse and download books
  - Author: Upload and manage books, plus reader permissions
  - Admin: Full system access including user management
- **Session Security**: Configurable session secret key with fallback for development

### File Management System
- **Upload Restrictions**: PDF files only, maximum 16MB file size
- **Storage Strategy**: Secure filename generation and organized file storage
- **Download Tracking**: Built-in download counter for each book

### User Interface Design
- **Responsive Design**: Mobile-first Bootstrap layout with dark theme
- **Navigation**: Role-aware navigation menu showing appropriate options
- **Search and Filter**: Advanced search functionality with category filtering
- **Dashboard Views**: Role-specific dashboards (admin panel, user profiles)

## External Dependencies

### CSS and JavaScript Libraries
- **Bootstrap 5**: CSS framework loaded from Replit CDN with dark theme variant
- **Font Awesome 6.4.0**: Icon library loaded from CDNJS for UI icons

### Python Libraries
- **Flask**: Core web framework for routing, templating, and request handling
- **Werkzeug**: Security utilities for password hashing and file handling
- **Standard Library**: hashlib, uuid, datetime, os for core functionality

### Development Environment
- **Static Assets**: Custom CSS and JavaScript files served from static directory
- **Template System**: Jinja2 templates with inheritance for consistent layout
- **Logging**: Python logging module configured for debugging

### File System Dependencies
- **Upload Directory**: Local 'uploads' folder for PDF file storage
- **Static Assets**: CSS, JavaScript, and other static files served from 'static' directory
- **Templates**: HTML templates organized in 'templates' directory with base template inheritance