"""
RAG Retriever - Truy xuất thông tin từ Vector Store
"""
from config.config import config
from backend.rag.embeddings import EmbeddingModel
from backend.database.vector_store import VectorStore
import sys
from pathlib import Path
from typing import List, Dict

# Import modules
sys.path.append(str(Path(__file__).parent.parent.parent))


class RAGRetriever:
    """Class để retrieve documents từ vector store"""

    def __init__(
        self,
        vector_store: VectorStore = None,
        embedder: EmbeddingModel = None,
        top_k: int = None
    ):
        """
        Khởi tạo RAG Retriever

        Args:
            vector_store: Vector store instance (nếu None sẽ tạo mới)
            embedder: Embedding model (nếu None sẽ tạo mới)
            top_k: Số documents trả về
        """
        self.top_k = top_k or config.TOP_K_RETRIEVAL

        # Khởi tạo embedder
        if embedder:
            self.embedder = embedder
        else:
            print("⏳ Đang khởi tạo Embedding Model...")
            self.embedder = EmbeddingModel(use_vietnamese=False)

        # Khởi tạo vector store
        if vector_store:
            self.vector_store = vector_store
        else:
            print("⏳ Đang khởi tạo Vector Store...")
            self.vector_store = VectorStore(
                dimension=self.embedder.embedding_dim)

            # Thử load vector store có sẵn
            self.load_vector_store()

        print(f"✅ RAG Retriever sẵn sàng! (Top-K: {self.top_k})")

    def load_vector_store(self, path: str = None) -> bool:
        """
        Load vector store từ file

        Args:
            path: Đường dẫn (nếu None dùng path mặc định)

        Returns:
            bool: True nếu load thành công
        """
        load_path = path or str(
            config.VECTOR_STORE_DIR / "health_chatbot_index")
        success = self.vector_store.load(load_path)

        if success:
            print(
                f"✅ Đã load vector store: {self.vector_store.index.ntotal} documents")
        else:
            print("⚠️  Chưa có vector store. Hãy build trước bằng build_rag_pipeline.py")

        return success

    def retrieve(self, query: str, top_k: int = None) -> List[Dict]:
        """
        Truy xuất documents liên quan đến query

        Args:
            query: Câu hỏi/query
            top_k: Số documents trả về (nếu None dùng self.top_k)

        Returns:
            List[Dict]: Danh sách documents với content, metadata, score
        """
        k = top_k or self.top_k

        # Encode query
        query_embedding = self.embedder.encode_text(query)

        # Search trong vector store
        results = self.vector_store.search(query_embedding, top_k=k)

        return results

    def retrieve_with_threshold(
        self,
        query: str,
        similarity_threshold: float = 0.5,
        top_k: int = None
    ) -> List[Dict]:
        """
        Retrieve documents với ngưỡng similarity tối thiểu

        Args:
            query: Câu hỏi
            similarity_threshold: Ngưỡng similarity (0-1)
            top_k: Số documents tối đa

        Returns:
            List[Dict]: Documents có similarity >= threshold
        """
        results = self.retrieve(query, top_k)

        # Filter theo threshold
        filtered = [
            doc for doc in results
            if doc.get('similarity', 0) >= similarity_threshold
        ]

        return filtered

    def retrieve_and_format(self, query: str, top_k: int = None) -> str:
        """
        Retrieve và format thành context string

        Args:
            query: Câu hỏi
            top_k: Số documents

        Returns:
            str: Formatted context
        """
        results = self.retrieve(query, top_k)

        if not results:
            return "Không tìm thấy thông tin liên quan."

        context_parts = []

        for i, doc in enumerate(results, 1):
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            source = metadata.get('source', 'Unknown')
            similarity = doc.get('similarity', 0)

            context_parts.append(
                f"[Tài liệu {i} - Nguồn: {source} - Độ liên quan: {similarity:.2f}]\n{content}"
            )

        return "\n\n---\n\n".join(context_parts)

    def get_stats(self) -> Dict:
        """Lấy thống kê về retriever"""
        vs_stats = self.vector_store.get_stats()

        return {
            'vector_store': vs_stats,
            'embedding_dim': self.embedder.embedding_dim,
            'top_k': self.top_k,
            'total_documents': vs_stats['total_documents']
        }


def demo_retriever():
    """Demo RAG Retriever"""
    print("=" * 70)
    print("DEMO - RAG RETRIEVER")
    print("=" * 70)

    # Tạo retriever
    retriever = RAGRetriever()

    # Kiểm tra vector store
    stats = retriever.get_stats()
    print(f"\n📊 Thống kê Retriever:")
    print(f"  - Total documents: {stats['total_documents']}")
    print(f"  - Embedding dimension: {stats['embedding_dim']}")
    print(f"  - Top-K: {stats['top_k']}")

    if stats['total_documents'] == 0:
        print("\n⚠️  Vector store trống! Hãy chạy build_rag_pipeline.py trước.")
        return

    # Test queries
    print("\n" + "=" * 70)
    print("TEST RETRIEVAL")
    print("=" * 70)

    queries = [
        "Cảm cúm có triệu chứng gì?",
        "Làm sao để chữa đau đầu?",
        "Khi nào cần đi bác sĩ?",
        "Cách phòng ngừa bệnh hiệu quả"
    ]

    for query in queries:
        print(f"\n{'='*70}")
        print(f"❓ Query: {query}")
        print(f"{'='*70}")

        # Retrieve
        results = retriever.retrieve(query, top_k=3)

        if not results:
            print("  ⚠️  Không tìm thấy kết quả")
            continue

        print(f"\n🔍 Top 3 kết quả:\n")

        for i, doc in enumerate(results, 1):
            print(f"  [{i}] Similarity: {doc['similarity']:.3f}")
            print(f"      Source: {doc['metadata']['source']}")
            print(f"      Content: {doc['content'][:120]}...")
            print()

    # Test retrieve với threshold
    print("\n" + "=" * 70)
    print("TEST RETRIEVE VỚI THRESHOLD")
    print("=" * 70)

    query = "điều trị cảm cúm"
    threshold = 0.6

    print(f"\n❓ Query: {query}")
    print(f"🎯 Threshold: {threshold}")

    results = retriever.retrieve_with_threshold(
        query, similarity_threshold=threshold)

    print(f"\n📊 Kết quả (similarity >= {threshold}):")
    print(f"  Tìm thấy {len(results)} documents\n")

    for i, doc in enumerate(results, 1):
        print(f"  [{i}] {doc['similarity']:.3f} - {doc['content'][:80]}...")

    # Test format context
    print("\n" + "=" * 70)
    print("TEST FORMAT CONTEXT")
    print("=" * 70)

    query = "triệu chứng sốt"
    print(f"\n❓ Query: {query}\n")

    context = retriever.retrieve_and_format(query, top_k=2)
    print("📄 Context formatted:")
    print("-" * 70)
    print(context)
    print("-" * 70)

    print("\n✅ Demo hoàn tất!")


if __name__ == "__main__":
    demo_retriever()
