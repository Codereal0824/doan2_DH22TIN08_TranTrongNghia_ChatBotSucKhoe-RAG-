"""
Config Module - Quản lý cấu hình ứng dụng (Đã tối ưu RAG Y Tế)
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """Cấu hình chung cho ứng dụng"""

    # ============ GROQ API ============
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')

    # ============ SQL SERVER ============
    SQL_SERVER = os.getenv('SQL_SERVER', 'localhost')
    SQL_DATABASE = os.getenv('SQL_DATABASE', 'HealthChatbotDB')
    SQL_USERNAME = os.getenv('SQL_USERNAME', 'sa')
    SQL_PASSWORD = os.getenv('SQL_PASSWORD')
    SQL_PORT = os.getenv('SQL_PORT', '1433')
    SQL_DRIVER = os.getenv('SQL_DRIVER', 'ODBC Driver 17 for SQL Server')

    @property
    def SQL_CONNECTION_STRING(self):
        """Tạo connection string cho SQL Server"""
        return (
            f"DRIVER={{{self.SQL_DRIVER}}};"
            f"SERVER={self.SQL_SERVER},{self.SQL_PORT};"
            f"DATABASE={self.SQL_DATABASE};"
            f"UID={self.SQL_USERNAME};"
            f"PWD={self.SQL_PASSWORD};"
            "TrustServerCertificate=yes;"
        )

    # ============ VECTOR DATABASE ============
    VECTOR_DB_TYPE = os.getenv('VECTOR_DB_TYPE', 'faiss')
    VECTOR_DB_PATH = os.getenv('VECTOR_DB_PATH', './data/vector_store')

    # ============ EMBEDDING ============
    # Sửa lỗi: Gán đúng biến env cho từng model
    EMBEDDING_MODEL = os.getenv(
        'EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
    EMBEDDING_MODEL_VI = os.getenv(
        'EMBEDDING_MODEL_VI', 'VoVanPhuc/sup-SimCSE-VietNamese-phobert-base')

    # ============ RAG SETTINGS ============
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 1000))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 200))

    # --- Cấu hình Truy xuất lai (Hybrid Search) ---
    # Stage 1: Lấy nhiều candidate để bao phủ mọi bệnh chứa triệu chứng (ví dụ: Sốt, Ho...)
    TOP_K_INITIAL = int(os.getenv('TOP_K_INITIAL', 20))
    # Stage 2: Kết quả cuối cùng đưa vào Prompt. Ép xuống 3 để tránh AI bị "ngáo" vì trộn lẫn bệnh
    TOP_K_RETRIEVAL = int(os.getenv('TOP_K_RETRIEVAL', 3))

    # Ép AI trả lời ngắn gọn, tối đa 3 câu (khoảng 256-512 tokens)
    MAX_TOKENS = int(os.getenv('MAX_TOKENS', 512))

    # Hằng số RRF (Reciprocal Rank Fusion) cân bằng Dense/Sparse Retrieval
    RRF_K = int(os.getenv('RRF_K', 60))

    # 0.1 = Tối đa hóa tính kỷ luật, cấm AI sáng tạo bừa bãi ngoài tài liệu y khoa
    TEMPERATURE = float(os.getenv('TEMPERATURE', 0.1))

    # --- Ngưỡng Lọc (Thresholds) ---
    # FAISS Relevance Threshold (L2 distance - càng thấp càng tốt)
    RELEVANCE_THRESHOLD = float(os.getenv('RELEVANCE_THRESHOLD', 150.0))

    # Semantic Similarity Threshold (Cosine similarity: 0-1, càng cao càng tốt)
    # Hạ xuống 0.25 để cho phép các câu hỏi rất ngắn (vd: "đau bụng") lọt qua vòng lọc
    SEMANTIC_THRESHOLD = float(os.getenv('SEMANTIC_THRESHOLD', 0.25))

    # ============ FLASK & SERVER ============
    # Thêm lại cấu hình Flask bị thiếu để không lỗi phần test bên dưới
    FLASK_PORT = os.getenv('FLASK_PORT', '5000')
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')

    # ============ DEBUG MODE ============
    DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

    # ============ LOGGING ============
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/chatbot.log')

    # ============ SECURITY ============
    RATE_LIMIT = os.getenv('RATE_LIMIT', '100 per hour')
    CORS_ORIGINS = os.getenv(
        'CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000').split(',')

    # ============ PATHS ============
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / 'data'
    HEALTH_KNOWLEDGE_DIR = DATA_DIR / 'health_knowledge'
    VECTOR_STORE_DIR = DATA_DIR / 'vector_store'
    LOGS_DIR = BASE_DIR / 'logs'

    @classmethod
    def validate(cls):
        """Kiểm tra các cấu hình bắt buộc"""
        errors = []

        if not cls.GROQ_API_KEY:
            errors.append("❌ GROQ_API_KEY chưa được cấu hình")

        if not cls.SQL_PASSWORD:
            errors.append("❌ SQL_PASSWORD chưa được cấu hình")

        if errors:
            print("\n🚨 LỖI CẤU HÌNH:")
            for error in errors:
                print(f"  {error}")
            print("\n💡 Vui lòng kiểm tra file config/.env\n")
            return False

        print("✅ Cấu hình hợp lệ!")
        return True

    @classmethod
    def create_directories(cls):
        """Tạo các thư mục cần thiết"""
        directories = [
            cls.DATA_DIR,
            cls.HEALTH_KNOWLEDGE_DIR,
            cls.VECTOR_STORE_DIR,
            cls.LOGS_DIR
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        print("✅ Đã tạo các thư mục cần thiết")


# Tạo instance config
config = Config()


if __name__ == "__main__":
    # Test cấu hình
    print("=" * 50)
    print("KIỂM TRA CẤU HÌNH CHATBOT (RAG Y TẾ)")
    print("=" * 50)

    config.create_directories()
    config.validate()

    print("\n📊 Thông tin cấu hình:")
    print(f"  - Groq Model: {config.GROQ_MODEL}")
    print(f"  - SQL Server: {config.SQL_SERVER}")
    print(f"  - SQL Database: {config.SQL_DATABASE}")
    print(f"  - Vector DB: {config.VECTOR_DB_TYPE}")
    print(f"  - Chunk Size: {config.CHUNK_SIZE}")
    print(f"  - Top K Retrieval: {config.TOP_K_RETRIEVAL}")
    print(f"  - Flask Port: {config.FLASK_PORT}")
