"""
SQL Handler - Quản lý kết nối và truy vấn SQL Server (Cập nhật cho Chatbot RAG)
"""
from config.config import config
import sys
from pathlib import Path
import pyodbc
from typing import List, Dict

# =====================================================================
# Tiền xử lý đường dẫn (Path manipulation):
# Đảm bảo Python luôn nhận diện được thư mục gốc của dự án,
# tránh các lỗi 'ModuleNotFoundError' khi import config từ các module khác.
# =====================================================================
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Lớp SQLHandler áp dụng mẫu thiết kế (Design Pattern) chuyên biệt cho Database.
# Quản lý vòng đời của Connection và Cursor, đảm bảo tài nguyên được giải phóng đúng lúc.


class SQLHandler:
    """Class quản lý kết nối và truy vấn SQL Server"""

    def __init__(self):
        """Khởi tạo connection"""
        self.connection = None
        self.cursor = None

    # Hàm mở kết nối đến CSDL. Sử dụng thư viện pyodbc và chuỗi kết nối
    # được bảo mật trong file cấu hình (config).
    def connect(self) -> bool:
        try:
            self.connection = pyodbc.connect(config.SQL_CONNECTION_STRING)
            self.cursor = self.connection.cursor()
            print("Kết nối SQL Server thành công!")
            return True
        except Exception as e:
            print(f"Lỗi kết nối SQL Server: {e}")
            return False

    # Hàm ngắt kết nối: Cực kỳ quan trọng để chống rò rỉ bộ nhớ (Memory Leak)
    # và giải phóng các kết nối (Connection Pool) cho SQL Server.
    def disconnect(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        print("Đã ngắt kết nối SQL Server")

    # Hàm thực thi các câu lệnh lấy dữ liệu (SELECT).
    # Nhận vào câu truy vấn và tham số (để chống SQL Injection).
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)

            # Thuật toán ánh xạ (Mapping): Tự động trích xuất tên cột (columns) từ CSDL
            # và gép nối (zip) với từng dòng dữ liệu (row) để tạo thành danh sách các Dictionary.
            # Điều này giúp tầng logic xử lý dễ dàng gọi data['tên_cột'] thay vì gọi theo index (row[0]).
            columns = [column[0] for column in self.cursor.description]
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
        except Exception as e:
            print(f"Lỗi thực thi query: {e}")
            return []

    # Hàm thực thi các câu lệnh thay đổi dữ liệu (INSERT, UPDATE, DELETE).
    # Có tích hợp cơ chế Transaction (Giao dịch) để đảm bảo tính toàn vẹn dữ liệu (ACID).
    def execute_non_query(self, query: str, params: tuple = None) -> bool:
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)

            # Commit: Xác nhận lưu các thay đổi vào ổ cứng vĩnh viễn.
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Lỗi thực thi: {e}")
            # Rollback: Nếu có bất kỳ lỗi nào xảy ra giữa chừng, hoàn tác toàn bộ thao tác,
            # tránh tình trạng dữ liệu bị ghi thiếu hoặc rác (Dirty Data).
            self.connection.rollback()
            return False

    # Hàm khởi tạo một phiên chat mới cho người dùng.
    def create_chat_session(self, user_id: int, session_name: str = "Đoạn chat mới") -> int:
        # Sử dụng mệnh đề 'OUTPUT INSERTED.session_id' để trả về ngay lập tức
        # ID của dòng vừa được tạo ra mà không cần phải thực thi thêm một câu lệnh SELECT nữa.
        query = """
            INSERT INTO chat_sessions (user_id, session_name)
            OUTPUT INSERTED.session_id
            VALUES (?, ?)
        """
        try:
            self.cursor.execute(query, (user_id, session_name))
            session_id = self.cursor.fetchone()[0]
            self.connection.commit()
            return session_id
        except Exception as e:
            print(f"Lỗi tạo session: {e}")
            self.connection.rollback()
            return -1

    # Hàm lấy danh sách các phiên chat của một user, sắp xếp theo thời gian giảm dần (mới nhất xếp trên).
    def get_user_sessions(self, user_id: int) -> List[Dict]:
        query = """
            SELECT session_id, session_name, created_at 
            FROM chat_sessions 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        """
        return self.execute_query(query, (user_id,))

    # Hàm lưu trữ chi tiết từng tin nhắn vào lịch sử.
    def save_chat_message(self, session_id: int, sender_type: str, message_text: str) -> bool:
        # Kiểm tra tính hợp lệ của dữ liệu ở mức ứng dụng (Application Level Validation)
        # trước khi đẩy xuống CSDL để đối chiếu với ràng buộc CHECK CONSTRAINT.
        if sender_type not in ['USER', 'BOT']:
            print("Lỗi: sender_type chỉ được là 'USER' hoặc 'BOT'")
            return False

        query = """
            INSERT INTO chat_history (session_id, sender_type, message_text)
            VALUES (?, ?, ?)
        """
        return self.execute_non_query(query, (session_id, sender_type, message_text))

    # Hàm tải lại toàn bộ lịch sử tin nhắn của một phiên chat cụ thể để hiển thị lên UI,
    # sắp xếp theo thời gian tăng dần (cũ nhất ở trên cùng).
    def get_chat_history(self, session_id: int) -> List[Dict]:
        query = """
            SELECT sender_type, message_text, created_at 
            FROM chat_history 
            WHERE session_id = ? 
            ORDER BY created_at ASC
        """
        return self.execute_query(query, (session_id,))
