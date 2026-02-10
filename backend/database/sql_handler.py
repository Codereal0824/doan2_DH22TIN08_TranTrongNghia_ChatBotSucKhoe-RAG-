"""
SQL Handler - Quản lý kết nối và truy vấn SQL Server
"""
from config.config import config
import pyodbc
from typing import List, Dict, Optional
import sys
from pathlib import Path

# Thêm path để import config
sys.path.append(str(Path(__file__).parent.parent.parent))


class SQLHandler:
    """Class quản lý kết nối và truy vấn SQL Server"""

    def __init__(self):
        """Khởi tạo connection"""
        self.connection = None
        self.cursor = None

    def connect(self) -> bool:
        """
        Kết nối đến SQL Server

        Returns:
            bool: True nếu kết nối thành công
        """
        try:
            self.connection = pyodbc.connect(config.SQL_CONNECTION_STRING)
            self.cursor = self.connection.cursor()
            print("✅ Kết nối SQL Server thành công!")
            return True
        except Exception as e:
            print(f"❌ Lỗi kết nối SQL Server: {e}")
            return False

    def disconnect(self):
        """Đóng kết nối"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        print("🔌 Đã ngắt kết nối SQL Server")

    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """
        Thực thi câu lệnh SELECT

        Args:
            query: Câu lệnh SQL
            params: Tham số cho query (optional)

        Returns:
            List[Dict]: Danh sách kết quả dạng dictionary
        """
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)

            # Lấy tên cột
            columns = [column[0] for column in self.cursor.description]

            # Chuyển kết quả thành list of dict
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(zip(columns, row)))

            return results
        except Exception as e:
            print(f"❌ Lỗi thực thi query: {e}")
            return []

    def execute_non_query(self, query: str, params: tuple = None) -> bool:
        """
        Thực thi câu lệnh INSERT/UPDATE/DELETE

        Args:
            query: Câu lệnh SQL
            params: Tham số cho query (optional)

        Returns:
            bool: True nếu thành công
        """
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)

            self.connection.commit()
            print("✅ Thực thi thành công!")
            return True
        except Exception as e:
            print(f"❌ Lỗi thực thi: {e}")
            self.connection.rollback()
            return False

    # ==================== SYMPTOMS ====================

    def get_all_symptoms(self) -> List[Dict]:
        """Lấy tất cả triệu chứng"""
        query = "SELECT * FROM symptoms"
        return self.execute_query(query)

    def search_symptoms(self, keyword: str) -> List[Dict]:
        """
        Tìm kiếm triệu chứng theo từ khóa

        Args:
            keyword: Từ khóa tìm kiếm

        Returns:
            List[Dict]: Danh sách triệu chứng phù hợp
        """
        query = """
            SELECT * FROM symptoms 
            WHERE symptom_name LIKE ? OR description LIKE ?
        """
        params = (f'%{keyword}%', f'%{keyword}%')
        return self.execute_query(query, params)

    def get_symptom_by_id(self, symptom_id: int) -> Optional[Dict]:
        """Lấy triệu chứng theo ID"""
        query = "SELECT * FROM symptoms WHERE id = ?"
        results = self.execute_query(query, (symptom_id,))
        return results[0] if results else None

    # ==================== DISEASES ====================

    def get_all_diseases(self) -> List[Dict]:
        """Lấy tất cả bệnh"""
        query = "SELECT * FROM diseases"
        return self.execute_query(query)

    def search_diseases(self, keyword: str) -> List[Dict]:
        """
        Tìm kiếm bệnh theo từ khóa

        Args:
            keyword: Từ khóa tìm kiếm

        Returns:
            List[Dict]: Danh sách bệnh phù hợp
        """
        query = """
            SELECT * FROM diseases 
            WHERE disease_name LIKE ? 
               OR description LIKE ?
               OR common_symptoms LIKE ?
        """
        params = (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%')
        return self.execute_query(query, params)

    def get_disease_by_id(self, disease_id: int) -> Optional[Dict]:
        """Lấy bệnh theo ID"""
        query = "SELECT * FROM diseases WHERE id = ?"
        results = self.execute_query(query, (disease_id,))
        return results[0] if results else None

    # ==================== RECOMMENDATIONS ====================

    def get_recommendations_by_symptom(self, symptom_id: int) -> List[Dict]:
        """
        Lấy khuyến nghị theo triệu chứng

        Args:
            symptom_id: ID của triệu chứng

        Returns:
            List[Dict]: Danh sách khuyến nghị
        """
        query = """
            SELECT r.*, s.symptom_name 
            FROM recommendations r
            JOIN symptoms s ON r.symptom_id = s.id
            WHERE r.symptom_id = ?
            ORDER BY 
                CASE r.priority
                    WHEN N'Khẩn cấp' THEN 1
                    WHEN N'Quan trọng' THEN 2
                    ELSE 3
                END
        """
        return self.execute_query(query, (symptom_id,))

    def get_all_recommendations(self) -> List[Dict]:
        """Lấy tất cả khuyến nghị"""
        query = """
            SELECT r.*, s.symptom_name 
            FROM recommendations r
            JOIN symptoms s ON r.symptom_id = s.id
        """
        return self.execute_query(query)

    # ==================== RAG HELPERS ====================

    def get_all_knowledge_for_rag(self) -> List[Dict]:
        """
        Lấy toàn bộ kiến thức từ database để đưa vào RAG

        Returns:
            List[Dict]: Danh sách documents với content và metadata
        """
        documents = []

        # Lấy triệu chứng
        symptoms = self.get_all_symptoms()
        for symptom in symptoms:
            doc = {
                'content': f"Triệu chứng: {symptom['symptom_name']}\n"
                f"Mô tả: {symptom['description']}\n"
                f"Mức độ: {symptom['severity_level']}",
                'metadata': {
                    'source': 'SQL Server - symptoms',
                    'type': 'symptom',
                    'id': symptom['id'],
                    'name': symptom['symptom_name']
                }
            }
            documents.append(doc)

        # Lấy bệnh
        diseases = self.get_all_diseases()
        for disease in diseases:
            doc = {
                'content': f"Bệnh: {disease['disease_name']}\n"
                f"Mô tả: {disease['description']}\n"
                f"Triệu chứng phổ biến: {disease['common_symptoms']}\n"
                f"Phòng ngừa: {disease['prevention']}",
                'metadata': {
                    'source': f"SQL Server - diseases | {disease['source_document']}",
                    'type': 'disease',
                    'id': disease['id'],
                    'name': disease['disease_name']
                }
            }
            documents.append(doc)

        # Lấy khuyến nghị
        recommendations = self.get_all_recommendations()
        for rec in recommendations:
            doc = {
                'content': f"Khuyến nghị cho '{rec['symptom_name']}':\n"
                f"{rec['recommendation_text']}\n"
                f"Mức độ ưu tiên: {rec['priority']}",
                'metadata': {
                    'source': f"SQL Server - recommendations | {rec['source']}",
                    'type': 'recommendation',
                    'id': rec['id'],
                    'symptom': rec['symptom_name']
                }
            }
            documents.append(doc)

        print(f"✅ Đã lấy {len(documents)} documents từ SQL Server")
        return documents


def test_connection():
    """Test kết nối SQL Server"""
    print("=" * 60)
    print("TEST KẾT NỐI SQL SERVER")
    print("=" * 60)

    db = SQLHandler()

    # Test kết nối
    if not db.connect():
        print("❌ Không thể kết nối. Kiểm tra lại cấu hình!")
        return

    # Test query
    print("\n📊 Lấy danh sách triệu chứng:")
    symptoms = db.get_all_symptoms()
    print(f"  Tìm thấy {len(symptoms)} triệu chứng")

    print("\n📊 Lấy danh sách bệnh:")
    diseases = db.get_all_diseases()
    print(f"  Tìm thấy {len(diseases)} bệnh")

    print("\n📊 Lấy toàn bộ knowledge:")
    docs = db.get_all_knowledge_for_rag()
    print(f"  Tổng cộng: {len(docs)} documents")

    if docs:
        print(f"\n📄 Document mẫu:")
        print(f"  Content: {docs[0]['content'][:100]}...")
        print(f"  Source: {docs[0]['metadata']['source']}")

    db.disconnect()
    print("\n✅ Test hoàn tất!")


if __name__ == "__main__":
    test_connection()
