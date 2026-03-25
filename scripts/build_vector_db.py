"""
Script build Vector Database cho Health Chatbot
Sử dụng code tự viết thay vì langchain
"""
from backend.database.vector_store import VectorStore
from backend.rag.embeddings import EmbeddingModel
from backend.utils.chunking import DocumentChunker
from backend.utils.document_loader import DocumentLoader
from config.config import config
import sys
from pathlib import Path

# Thao tác can thiệp đường dẫn hệ thống (Path Manipulation).
# Cực kỳ cần thiết đối với các Script chạy độc lập (Standalone Script) nằm sâu trong cây thư mục,
# giúp Python nhận diện được thư mục gốc của dự án để import các module nội bộ mà không văng lỗi 'ModuleNotFoundError'.
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Hàm thực thi Quy trình ETL (Extract - Transform - Load) cốt lõi của hệ thống RAG.


def build_vector_database():
    """Xây dựng vector database từ data"""
    print("=" * 70)
    print("[TIEN TRINH] XAY DUNG VECTOR DATABASE (OFFLINE INDEXING PIPELINE)")
    print("=" * 70)

    # ============================================
    # BƯỚC 1: EXTRACT (TRÍCH XUẤT DỮ LIỆU)
    # ============================================
    print("\n[BUOC 1] LOAD DOCUMENTS")
    print("-" * 70)

    # Khởi tạo đối tượng DocumentLoader để quét toàn bộ thư mục tri thức y khoa.
    loader = DocumentLoader()
    documents = loader.load_directory(
        str(config.DATA_DIR / "health_knowledge"))

    if not documents:
        print("[LOI] Khong tim thay documents nao trong thu muc quy dinh!")
        return False

    print(f"[THANH CONG] Da load {len(documents)} documents")

    # ============================================
    # BƯỚC 2: TRANSFORM 1 - DATA PREPROCESSING (TIỀN XỬ LÝ VÀ PHÂN MẢNH)
    # ============================================
    print("\n[BUOC 2] CHUNKING DOCUMENTS")
    print("-" * 70)
    print("[THONG TIN] Using Section-Based Chunking for structured documents")

    # Ép buộc sử dụng cơ chế Semantic Chunking (use_section_based=True)
    # để đảm bảo tính toàn vẹn ngữ nghĩa của các tài liệu y tế thay vì cắt ngẫu nhiên.
    chunker = DocumentChunker(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        use_section_based=True
    )
    chunks = chunker.chunk_documents(documents)

    print(f"[THANH CONG] Da chia thanh {len(chunks)} chunks")

    # ============================================
    # BƯỚC 3: TRANSFORM 2 - FEATURE EXTRACTION (TRÍCH XUẤT ĐẶC TRƯNG VECTOR)
    # ============================================
    print("\n[BUOC 3] ENCODE DOCUMENTS")
    print("-" * 70)

    # Khởi tạo Mô hình học sâu (Sentence Transformers) để nhúng văn bản.
    # Quá trình này sẽ đẩy các chunks qua mô hình Mạng nơ-ron (Neural Network)
    # để chuyển đổi thành các ma trận số thực (Embeddings).
    embedder = EmbeddingModel()
    encoded_docs = embedder.encode_documents(chunks)

    print(f"[THANH CONG] Da encode {len(encoded_docs)} documents")

    # ============================================
    # BƯỚC 4: LOAD - INDEXING (LẬP CHỈ MỤC)
    # ============================================
    print("\n[BUOC 4] BUILD VECTOR STORE")
    print("-" * 70)

    # Cấu trúc hóa các Vector vào không gian nhiều chiều của FAISS.
    vector_store = VectorStore(
        dimension=embedder.embedding_dim,
        index_path=str(config.VECTOR_STORE_DIR / "health_faiss.index")
    )
    # Nạp mảng Vector kèm Siêu dữ liệu (Metadata) vào RAM.
    vector_store.add_documents(encoded_docs)

    # ============================================
    # BƯỚC 5: SERIALIZATION (TUẦN TỰ HÓA & LƯU TRỮ VĨNH VIỄN)
    # ============================================
    print("\n[BUOC 5] SAVE VECTOR STORE")
    print("-" * 70)

    # Kết xuất (Dump) toàn bộ cấu trúc Cây chỉ mục (Index) từ RAM xuống Ổ cứng (Disk)
    # thành các tệp tin nhị phân (.faiss và .pkl).
    vector_store.save()

    # ============================================
    # BƯỚC 6: REPORTING (BÁO CÁO THỐNG KÊ)
    # ============================================
    print("\n[BUOC 6] THONG KE")
    print("-" * 70)
    stats = vector_store.get_stats()
    for key, value in stats.items():
        print(f"  [CHI TIET] {key}: {value}")

    print("\n" + "=" * 70)
    print("[THANH CONG] XAY DUNG VECTOR DATABASE HOAN TAT!")
    print("=" * 70)

    return True


# Khối lệnh khởi động hệ thống (Entry Point)
if __name__ == "__main__":
    # Tự động tạo thư mục chứa cơ sở dữ liệu nếu nó chưa tồn tại (Infrastructure as Code)
    config.VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

    # Kích hoạt tiến trình Build Database
    success = build_vector_database()

    if not success:
        print("\n[LOI] Xay dung database that bai! He thong dung hoat dong.")
        # Thoát chương trình với mã lỗi (Exit Code 1) để báo hiệu cho hệ điều hành
        sys.exit(1)

    print(
        "\n[THONG TIN] Bay gio ban co the khoi dong Web Server Flask de chay Chatbot!")
