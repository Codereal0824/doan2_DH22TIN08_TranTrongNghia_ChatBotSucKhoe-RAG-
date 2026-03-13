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

# Add project root to path FIRST
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def build_vector_database():
    """Xây dựng vector database từ data"""
    print("=" * 70)
    print("🔧 XÂY DỰNG VECTOR DATABASE")
    print("=" * 70)

    # 1. Load documents
    print("\n1️⃣  LOAD DOCUMENTS")
    print("-" * 70)
    loader = DocumentLoader()
    documents = loader.load_directory(
        str(config.DATA_DIR / "health_knowledge"))

    if not documents:
        print("❌ Không tìm thấy documents nào!")
        return False

    print(f"✅ Đã load {len(documents)} documents")

    # 2. Chunk documents
    print("\n2️⃣  CHUNKING DOCUMENTS")
    print("-" * 70)
    print("📊 Using Section-Based Chunking for structured documents")
    chunker = DocumentChunker(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        use_section_based=True  # NEW: Use section-based chunking
    )
    chunks = chunker.chunk_documents(documents)

    print(f"✅ Đã chia thành {len(chunks)} chunks")

    # 3. Encode documents
    print("\n3️⃣  ENCODE DOCUMENTS")
    print("-" * 70)
    embedder = EmbeddingModel()  # Sử dụng giá trị mặc định
    encoded_docs = embedder.encode_documents(chunks)

    print(f"✅ Đã encode {len(encoded_docs)} documents")

    # 4. Build vector store
    print("\n4️⃣  BUILD VECTOR STORE")
    print("-" * 70)
    vector_store = VectorStore(
        dimension=embedder.embedding_dim,
        index_path=str(config.VECTOR_STORE_DIR / "health_faiss.index")
    )
    vector_store.add_documents(encoded_docs)

    # 5. Save vector store
    print("\n5️⃣  SAVE VECTOR STORE")
    print("-" * 70)
    vector_store.save()

    # 6. Stats
    print("\n6️⃣  THỐNG KÊ")
    print("-" * 70)
    stats = vector_store.get_stats()
    for key, value in stats.items():
        print(f"  📊 {key}: {value}")

    print("\n" + "=" * 70)
    print("✅ XÂY DỰNG VECTOR DATABASE THÀNH CÔNG!")
    print("=" * 70)

    return True


if __name__ == "__main__":
    # Tạo thư mục vector store nếu chưa có
    config.VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

    # Build database
    success = build_vector_database()

    if not success:
        print("\n❌ Xây dựng database thất bại!")
        sys.exit(1)

    print("\n💡 Bây giờ bạn có thể chạy chatbot!")
