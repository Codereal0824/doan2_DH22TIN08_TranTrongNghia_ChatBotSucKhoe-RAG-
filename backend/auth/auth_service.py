"""
Authentication Service - Xử lý đăng ký và đăng nhập
"""
from werkzeug.security import generate_password_hash, check_password_hash
from backend.database.sql_handler import SQLHandler
from datetime import datetime
from typing import Optional, Dict, Tuple


class AuthService:
    """Class quản lý authentication"""

    def __init__(self):
        """Khởi tạo auth service"""
        self.db = SQLHandler()

    def register_user(self, username: str, email: str, password: str,
                      confirm_password: str) -> Tuple[bool, str, Optional[int]]:
        """
        Đăng ký người dùng mới

        Args:
            username: Tên đăng nhập
            email: Email
            password: Mật khẩu
            confirm_password: Xác nhận mật khẩu

        Returns:
            Tuple[bool, str, Optional[int]]: (success, message, user_id)
        """
        try:
            # Validate input
            if not username or not email or not password:
                return False, "Vui lòng điền đầy đủ thông tin", None

            if len(username) < 3:
                return False, "Username phải có ít nhất 3 ký tự", None

            if len(password) < 6:
                return False, "Mật khẩu phải có ít nhất 6 ký tự", None

            if password != confirm_password:
                return False, "Mật khẩu xác nhận không khớp", None

            if '@' not in email or '.' not in email:
                return False, "Email không hợp lệ", None

            # Connect to database
            if not self.db.connect():
                return False, "Không thể kết nối database", None

            # Check if username exists
            check_username_query = "SELECT id FROM users WHERE username = ?"
            existing_user = self.db.execute_query(
                check_username_query, (username,))

            if existing_user:
                self.db.disconnect()
                return False, "Username đã tồn tại", None

            # Check if email exists
            check_email_query = "SELECT id FROM users WHERE email = ?"
            existing_email = self.db.execute_query(check_email_query, (email,))

            if existing_email:
                self.db.disconnect()
                return False, "Email đã được sử dụng", None

            # Hash password
            password_hash = generate_password_hash(password)

            # Insert new user
            insert_query = """
                INSERT INTO users (username, email, password_hash, role, created_at, is_active)
                VALUES (?, ?, ?, 'USER', GETDATE(), 1)
            """

            success = self.db.execute_non_query(
                insert_query, (username, email, password_hash))

            if not success:
                self.db.disconnect()
                return False, "Đăng ký thất bại, vui lòng thử lại", None

            # Get the newly created user ID
            get_user_query = "SELECT id FROM users WHERE username = ?"
            result = self.db.execute_query(get_user_query, (username,))

            self.db.disconnect()

            if result:
                user_id = result[0]['id']
                return True, "Đăng ký thành công!", user_id
            else:
                return True, "Đăng ký thành công!", None

        except Exception as e:
            if self.db.connection:
                self.db.disconnect()
            print(f"❌ Lỗi đăng ký: {e}")
            return False, f"Lỗi hệ thống: {str(e)}", None

    def login_user(self, username: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Đăng nhập người dùng

        Args:
            username: Username hoặc email
            password: Mật khẩu

        Returns:
            Tuple[bool, str, Optional[Dict]]: (success, message, user_data)
        """
        try:
            # Validate input
            if not username or not password:
                return False, "Vui lòng nhập đầy đủ thông tin", None

            # Connect to database
            if not self.db.connect():
                return False, "Không thể kết nối database", None

            # Query user by username or email
            query = """
                SELECT id, username, email, password_hash, role, is_active
                FROM users
                WHERE (username = ? OR email = ?) AND is_active = 1
            """

            result = self.db.execute_query(query, (username, username))

            if not result:
                self.db.disconnect()
                return False, "Tài khoản không tồn tại hoặc đã bị khóa", None

            user_data = result[0]

            # Check password
            if not check_password_hash(user_data['password_hash'], password):
                self.db.disconnect()
                return False, "Mật khẩu không chính xác", None

            # Update last login time
            update_query = "UPDATE users SET last_login = GETDATE() WHERE id = ?"
            self.db.execute_non_query(update_query, (user_data['id'],))

            self.db.disconnect()

            # Return user info (without password hash)
            user_info = {
                'id': user_data['id'],
                'username': user_data['username'],
                'email': user_data['email'],
                'role': user_data['role']
            }

            return True, "Đăng nhập thành công!", user_info

        except Exception as e:
            if self.db.connection:
                self.db.disconnect()
            print(f"❌ Lỗi đăng nhập: {e}")
            return False, f"Lỗi hệ thống: {str(e)}", None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """
        Lấy thông tin user theo ID

        Args:
            user_id: ID của user

        Returns:
            Optional[Dict]: Thông tin user hoặc None
        """
        try:
            if not self.db.connect():
                return None

            query = """
                SELECT id, username, email, role, created_at, last_login
                FROM users
                WHERE id = ? AND is_active = 1
            """

            result = self.db.execute_query(query, (user_id,))
            self.db.disconnect()

            if result:
                return result[0]
            return None

        except Exception as e:
            if self.db.connection:
                self.db.disconnect()
            print(f"❌ Lỗi lấy thông tin user: {e}")
            return None

    def change_password(self, user_id: int, old_password: str,
                        new_password: str, confirm_password: str) -> Tuple[bool, str]:
        """
        Đổi mật khẩu

        Args:
            user_id: ID người dùng
            old_password: Mật khẩu cũ
            new_password: Mật khẩu mới
            confirm_password: Xác nhận mật khẩu mới

        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Validate
            if len(new_password) < 6:
                return False, "Mật khẩu mới phải có ít nhất 6 ký tự"

            if new_password != confirm_password:
                return False, "Mật khẩu xác nhận không khớp"

            # Connect
            if not self.db.connect():
                return False, "Không thể kết nối database"

            # Get current password hash
            query = "SELECT password_hash FROM users WHERE id = ?"
            result = self.db.execute_query(query, (user_id,))

            if not result:
                self.db.disconnect()
                return False, "Người dùng không tồn tại"

            # Verify old password
            if not check_password_hash(result[0]['password_hash'], old_password):
                self.db.disconnect()
                return False, "Mật khẩu cũ không chính xác"

            # Update password
            new_hash = generate_password_hash(new_password)
            update_query = """
                UPDATE users 
                SET password_hash = ?, updated_at = GETDATE()
                WHERE id = ?
            """

            success = self.db.execute_non_query(
                update_query, (new_hash, user_id))
            self.db.disconnect()

            if success:
                return True, "Đổi mật khẩu thành công!"
            else:
                return False, "Đổi mật khẩu thất bại"

        except Exception as e:
            if self.db.connection:
                self.db.disconnect()
            print(f"❌ Lỗi đổi mật khẩu: {e}")
            return False, f"Lỗi hệ thống: {str(e)}"
