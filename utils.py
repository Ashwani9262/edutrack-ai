import re
from functools import wraps
from flask import session, redirect, url_for, flash

EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash('Login required to access that page.', 'warning')
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view


def role_required(required_role):
    def decorator(view):
        @wraps(view)
        def wrapped_view(**kwargs):
            if session.get('role') != required_role:
                flash('You are not authorized to view that page.', 'danger')
                return redirect(url_for('dashboard'))
            return view(**kwargs)
        return wrapped_view
    return decorator


def validate_registration(name, email, password, college, role, class_id, class_ids):
    errors = []
    if not name or len(name.strip()) < 3:
        errors.append('Name must be at least 3 characters.')
    if not email or not EMAIL_PATTERN.match(email):
        errors.append('A valid email address is required.')
    if not password or len(password) < 6:
        errors.append('Password must be at least 6 characters long.')
    if not college or len(college.strip()) < 2:
        errors.append('College name is required.')
    if role not in ('student', 'teacher'):
        errors.append('Role selection is required.')
    if role == 'student' and not class_id:
        errors.append('Students must select one class.')
    if role == 'teacher' and not class_ids:
        errors.append('Teachers must select at least one class.')
    return errors
