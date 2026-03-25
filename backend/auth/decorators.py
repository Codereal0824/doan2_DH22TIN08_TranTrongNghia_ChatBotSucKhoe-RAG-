"""
Auth Decorators - Bảo vệ routes
"""
from functools import wraps
from flask import session, redirect, url_for, flash

# Decorator là một mẫu thiết kế (Design Pattern) trong Python, cho phép thay đổi
# hoặc mở rộng hành vi của một hàm mà không cần sửa đổi mã nguồn bên trong hàm đó.
# Trong ngữ cảnh ứng dụng web Flask, các decorators này đóng vai trò như Middleware,
# can thiệp vào Request trước khi nó chạm đến luồng xử lý chính (Controller).


def login_required(f):
    """
    Decorator yêu cầu đăng nhập
    Sử dụng: @login_required trước route handler
    """
    # functools.wraps giúp bảo tồn các siêu dữ liệu (metadata) của hàm gốc f
    # (như tên hàm, docstring) để Flask có thể định tuyến (routing) chính xác.
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Kiểm tra tính hợp lệ của Phiên làm việc (Session Validation).
        # Biến 'session' của Flask được lưu trữ an toàn phía server (hoặc mã hóa ở cookie).
        # Nếu khóa 'user_id' không tồn tại, có nghĩa là người dùng chưa xác thực.
        if 'user_id' not in session:
            # flash: Gửi một thông điệp tạm thời (hiển thị một lần) báo lỗi cho người dùng.
            flash('Vui lòng đăng nhập để tiếp tục', 'warning')
            # Chặn truy cập và tự động điều hướng (redirect) về trang đăng nhập.
            return redirect(url_for('login'))

        # Nếu đã có 'user_id' trong session, cho phép Request đi tiếp vào hàm f ban đầu.
        return f(*args, **kwargs)
    return decorated_function


# Hàm này triển khai cơ chế Kiểm soát truy cập dựa trên vai trò (Role-Based Access Control - RBAC).
# Rất cần thiết nếu sau này hệ thống phát triển thêm trang quản trị tài liệu y khoa.
def admin_required(f):
    """
    Decorator yêu cầu quyền admin
    Sử dụng: @admin_required trước route handler
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Lớp bảo vệ 1: Kiểm tra Xác thực (Authentication) - Xem đã đăng nhập chưa.
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để tiếp tục', 'warning')
            return redirect(url_for('login'))

        # Lớp bảo vệ 2: Kiểm tra Phân quyền (Authorization) - Xem có đủ thẩm quyền không.
        # Truy xuất khóa 'role' từ session và đối chiếu với hằng số 'ADMIN'.
        if session.get('role') != 'ADMIN':
            flash('Bạn không có quyền truy cập trang này', 'danger')
            # Nếu là USER thường định tò mò vào trang ADMIN, đẩy ngược về trang chủ (index).
            return redirect(url_for('index'))

        return f(*args, **kwargs)
    return decorated_function


# Hàm này dùng để điều hướng logic trải nghiệm người dùng (UX) và ngăn ngừa lỗi trạng thái.
# Chỉ áp dụng cho các route như /login hoặc /register.
def logout_required(f):
    """
    Decorator yêu cầu chưa đăng nhập (dùng cho trang login/register)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Nếu hệ thống phát hiện 'user_id' đã có trong session (tức là người dùng đang đăng nhập),
        # mà họ lại cố tình truy cập vào URL /login hoặc /register,
        # hệ thống sẽ chặn lại và đẩy thẳng họ vào màn hình Chat chính (index).
        if 'user_id' in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function
