"""
SQL Handler - Quản lý kết nối và truy vấn SQL Server (Cập nhật cho Chatbot RAG)
"""
from config.config import config
import sys
from pathlib import Path
import pyodbc
from typing import List, Dict

# =====================================================================
# Ép Python tìm thư mục gốc (Cái này phải nằm ở trên cùng)
# Lùi 3 cấp: database -> backend -> Chatbot_suckhoe
# =====================================================================
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# =====================================================================
# TỪ DÒNG 18 TRỞ ĐI MỚI ĐƯỢC IMPORT CONFIG
# =====================================================================


class SQLHandler:
    """Class quản lý kết nối và truy vấn SQL Server"""

    def __init__(self):
        """Khởi tạo connection"""
        self.connection = None
        self.cursor = None

    def connect(self) -> bool:
        try:
            self.connection = pyodbc.connect(config.SQL_CONNECTION_STRING)
            self.cursor = self.connection.cursor()
            print("✅ Kết nối SQL Server thành công!")
            return True
        except Exception as e:
            print(f"❌ Lỗi kết nối SQL Server: {e}")
            return False

    def disconnect(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        print("🔌 Đã ngắt kết nối SQL Server")

    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)

            columns = [column[0] for column in self.cursor.description]
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
        except Exception as e:
            print(f"❌ Lỗi thực thi query: {e}")
            return []

    def execute_non_query(self, query: str, params: tuple = None) -> bool:
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            self.connection.commit()
            return True
        except Exception as e:
            print(f"❌ Lỗi thực thi: {e}")
            self.connection.rollback()
            return False

    def create_chat_session(self, user_id: int, session_name: str = "Đoạn chat mới") -> int:
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
            print(f"❌ Lỗi tạo session: {e}")
            self.connection.rollback()
            return -1

    def get_user_sessions(self, user_id: int) -> List[Dict]:
        query = """
            SELECT session_id, session_name, created_at 
            FROM chat_sessions 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        """
        return self.execute_query(query, (user_id,))

    def save_chat_message(self, session_id: int, sender_type: str, message_text: str) -> bool:
        if sender_type not in ['USER', 'BOT']:
            print("❌ Lỗi: sender_type chỉ được là 'USER' hoặc 'BOT'")
            return False
        query = """
            INSERT INTO chat_history (session_id, sender_type, message_text)
            VALUES (?, ?, ?)
        """
        return self.execute_non_query(query, (session_id, sender_type, message_text))

    def get_chat_history(self, session_id: int) -> List[Dict]:
        query = """
            SELECT sender_type, message_text, created_at 
            FROM chat_history 
            WHERE session_id = ? 
            ORDER BY created_at ASC
        """
        return self.execute_query(query, (session_id,))


def test_connection():
    print("=" * 60)
    print("TEST KẾT NỐI SQL SERVER - CHATBOT RAG")
    print("=" * 60)
    db = SQLHandler()
    if not db.connect():
        print("❌ Không thể kết nối. Kiểm tra lại cấu hình!")
        return

    print("\n📊 Lấy danh sách Phiên chat của User ID = 1:")
    sessions = db.get_user_sessions(user_id=1)
    if sessions:
        print(f"  Tìm thấy {len(sessions)} phiên chat.")
    else:
        print("  Chưa có phiên chat nào hoặc User ID không tồn tại.")
    db.disconnect()
    print("\n✅ Test hoàn tất!")


if __name__ == "__main__":
    test_connection()
