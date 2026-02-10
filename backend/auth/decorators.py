"""
Auth Decorators - Bảo vệ routes
"""
from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    """
    Decorator yêu cầu đăng nhập
    Sử dụng: @login_required trước route handler
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để tiếp tục', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator yêu cầu quyền admin
    Sử dụng: @admin_required trước route handler
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để tiếp tục', 'warning')
            return redirect(url_for('login'))

        if session.get('role') != 'ADMIN':
            flash('Bạn không có quyền truy cập trang này', 'danger')
            return redirect(url_for('index'))

        return f(*args, **kwargs)
    return decorated_function


def logout_required(f):
    """
    Decorator yêu cầu chưa đăng nhập (dùng cho trang login/register)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function
