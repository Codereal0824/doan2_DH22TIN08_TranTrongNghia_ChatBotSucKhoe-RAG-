"""
Config Module - Quản lý cấu hình ứng dụng (Đã tối ưu RAG Y Tế)
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Nạp các biến môi trường (Environment Variables) từ tệp .env ẩn.
# Thao tác này tách biệt hoàn toàn Dữ liệu nhạy cảm (API Keys, Passwords)
# ra khỏi Source Code, giúp ngăn ngừa lộ lọt thông tin khi đẩy code lên Github.
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Lớp Config hoạt động như một Single Source of Truth (Nguồn Sự thật Duy nhất).
# Bất kỳ module nào trong dự án cần đọc tham số hệ thống đều phải truy xuất qua lớp này.


class Config:
    """Cấu hình chung cho ứng dụng"""

    # ============ GROQ API (LLM ENGINE) ============
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')

    # ============ CƠ SỞ DỮ LIỆU QUAN HỆ (SQL SERVER) ============
    SQL_SERVER = os.getenv('SQL_SERVER', 'localhost')
    SQL_DATABASE = os.getenv('SQL_DATABASE', 'HealthChatbotDB')
    SQL_USERNAME = os.getenv('SQL_USERNAME', 'sa')
    SQL_PASSWORD = os.getenv('SQL_PASSWORD')
    SQL_PORT = os.getenv('SQL_PORT', '1433')
    SQL_DRIVER = os.getenv('SQL_DRIVER', 'ODBC Driver 17 for SQL Server')

    # Sử dụng property decorator để tạo ra một thuộc tính động (Dynamic Property).
    # Chuỗi kết nối (Connection String) sẽ được tự động nội suy (interpolate)
    # mỗi khi được gọi, dựa trên các thông số môi trường hiện tại.
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

    # ============ CƠ SỞ DỮ LIỆU VECTOR (FAISS) ============
    VECTOR_DB_TYPE = os.getenv('VECTOR_DB_TYPE', 'faiss')
    VECTOR_DB_PATH = os.getenv('VECTOR_DB_PATH', './data/vector_store')

    # ============ MÔ HÌNH NHÚNG (EMBEDDING MODELS) ============
    # Khai báo riêng biệt mô hình tiếng Anh (MiniLM) phục vụ dự phòng tốc độ cao
    # và mô hình tiếng Việt (PhoBERT) phục vụ độ chính xác ngữ nghĩa sâu.
    EMBEDDING_MODEL = os.getenv(
        'EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
    EMBEDDING_MODEL_VI = os.getenv(
        'EMBEDDING_MODEL_VI', 'VoVanPhuc/sup-SimCSE-VietNamese-phobert-base')

    # ============ THÔNG SỐ RAG (HYPERPARAMETERS) ============

    # Kích thước khối (Chunk Size): Xác định lượng ký tự tối đa đưa vào LLM mỗi lần.
    # Độ chồng lấp (Overlap): Ngăn chặn việc cắt ngang câu, làm đứt gãy ngữ cảnh.
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 1000))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 200))

    # --- Cấu hình Truy xuất Lai (Hybrid Search Tuning) ---

    # Giai đoạn 1 (Candidate Generation):
    # Mở rộng dải quét (Top_K_Initial = 20) để đảm bảo độ Phủ (Recall) cao nhất,
    # gom toàn bộ các bệnh có chung một triệu chứng (VD: Sốt -> Cảm, Cúm, Sốt xuất huyết).
    TOP_K_INITIAL = int(os.getenv('TOP_K_INITIAL', 20))

    # Giai đoạn 2 (Context Injection):
    # Nén dải kết quả (Top_K_Retrieval = 4) trước khi đẩy vào Prompt LLM.
    # Tăng độ Chính xác (Precision) và tránh làm LLM bị nhiễu do nhồi nhét quá nhiều bệnh.
    TOP_K_RETRIEVAL = int(os.getenv('TOP_K_RETRIEVAL', 4))

    # Giới hạn số Token đầu ra để kiểm soát chi phí API và bắt buộc AI trả lời súc tích.
    MAX_TOKENS = int(os.getenv('MAX_TOKENS', 512))

    # Hằng số làm mượt (Smoothing Factor) cho thuật toán Reciprocal Rank Fusion.
    RRF_K = int(os.getenv('RRF_K', 60))

    # Nhiệt độ (Temperature) = 0.1: Đưa LLM vào trạng thái Xác định (Deterministic State).
    # Triệt tiêu sự sáng tạo, buộc AI phải trung thành tuyệt đối với tài liệu y khoa.
    TEMPERATURE = float(os.getenv('TEMPERATURE', 0.1))

    # --- Ngưỡng Lọc An toàn (Safety Thresholds) ---

    # Ngưỡng L2 Distance của FAISS: Điểm số càng nhỏ, hai vector càng gần nhau.
    # Các tài liệu có khoảng cách lớn hơn 150.0 sẽ bị loại bỏ hoàn toàn.
    RELEVANCE_THRESHOLD = float(os.getenv('RELEVANCE_THRESHOLD', 150.0))

    # Ngưỡng Cosine Similarity (Dành cho một số module dự phòng):
    # Hạ xuống 0.25 để nới lỏng bộ lọc cho các câu hỏi ngắn chỉ gồm 1-2 từ (vd: "đau bụng").
    SEMANTIC_THRESHOLD = float(os.getenv('SEMANTIC_THRESHOLD', 0.25))

    # ============ MÁY CHỦ WEB (FLASK SERVER) ============
    FLASK_PORT = os.getenv('FLASK_PORT', '5000')
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')

    # ============ MÔI TRƯỜNG PHÁT TRIỂN (ENV MODES) ============
    DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

    # ============ GHI NHẬT KÝ VÀ BẢO MẬT ============
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/chatbot.log')
    RATE_LIMIT = os.getenv('RATE_LIMIT', '100 per hour')
    CORS_ORIGINS = os.getenv(
        'CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000').split(',')

    # ============ CẤU TRÚC THƯ MỤC ẢO (VIRTUAL FILE SYSTEM) ============
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / 'data'
    HEALTH_KNOWLEDGE_DIR = DATA_DIR / 'health_knowledge'
    VECTOR_STORE_DIR = DATA_DIR / 'vector_store'
    LOGS_DIR = BASE_DIR / 'logs'

    @classmethod
    # Hàm tự kiểm tra (Self-validation) lúc khởi động ứng dụng.
    def validate(cls):
        """Kiểm tra các cấu hình bắt buộc"""
        errors = []

        if not cls.GROQ_API_KEY:
            errors.append("[LOI] GROQ_API_KEY chua duoc cau hinh")

        if not cls.SQL_PASSWORD:
            errors.append("[LOI] SQL_PASSWORD chua duoc cau hinh")

        if errors:
            print("\n[CANH BAO] LOI CAU HINH HE THONG:")
            for error in errors:
                print(f"  {error}")
            print("\nVui long kiem tra file config/.env\n")
            return False

        print("[THONG TIN] Cau hinh hop le!")
        return True

    @classmethod
    # Hàm tự động thiết lập hạ tầng ổ đĩa (Infrastructure Provisioning).
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

        print("[THONG TIN] Da tao cac thu muc can thiet")


# Áp dụng mẫu thiết kế Singleton: Khởi tạo một phiên bản duy nhất
# để toàn bộ hệ thống nạp chung cấu hình, tiết kiệm bộ nhớ RAM.
config = Config()


# Khối thực thi dành cho Unit Test độc lập
if __name__ == "__main__":
    print("=" * 50)
    print("KIEM TRA CAU HINH CHATBOT (RAG Y TE)")
    print("=" * 50)

    config.create_directories()
    config.validate()

    print("\n Thong tin cau hinh hien tai:")
    print(f"  - Groq Model: {config.GROQ_MODEL}")
    print(f"  - SQL Server: {config.SQL_SERVER}")
    print(f"  - SQL Database: {config.SQL_DATABASE}")
    print(f"  - Vector DB: {config.VECTOR_DB_TYPE}")
    print(f"  - Chunk Size: {config.CHUNK_SIZE}")
    print(f"  - Top K Retrieval: {config.TOP_K_RETRIEVAL}")
    print(f"  - Flask Port: {config.FLASK_PORT}")
