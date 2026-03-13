"""
Vector Store - Lưu trữ và tìm kiếm embeddings với FAISS
"""
from config.config import config
import faiss
import numpy as np
import pickle
from typing import List, Dict
from pathlib import Path
import sys

# Thêm path để import config
sys.path.append(str(Path(__file__).parent.parent.parent))


class VectorStore:
    """Class quản lý vector database với FAISS"""

    def __init__(self, dimension: int, index_path: str = None):
        """
        Khởi tạo Vector Store

        Args:
            dimension: Số chiều của vector embeddings
            index_path: Đường dẫn lưu/load index
        """
        self.dimension = dimension
        self.index_path = index_path or str(
            config.VECTOR_STORE_DIR / "faiss_index")

        # Tạo FAISS index (IndexFlatL2 = tìm kiếm chính xác)
        self.index = faiss.IndexFlatL2(dimension)

        # Lưu documents metadata
        self.documents = []

        print(f"✅ Khởi tạo Vector Store (dimension={dimension})")

    def add_documents(self, documents: List[Dict]):
        """
        Thêm documents vào vector store

        Args:
            documents: List[{'content': str, 'metadata': dict, 'embedding': np.ndarray}]
        """
        if not documents:
            print("⚠️  Không có document nào để thêm")
            return

        # Lấy embeddings
        embeddings = np.array([doc['embedding'] for doc in documents])

        # Kiểm tra dimension
        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Embedding dimension không khớp! "
                f"Expected {self.dimension}, got {embeddings.shape[1]}"
            )

        # Thêm vào FAISS index
        self.index.add(embeddings.astype('float32'))

        # Lưu metadata
        for doc in documents:
            doc_copy = {
                'content': doc['content'],
                'metadata': doc.get('metadata', {})
            }
            self.documents.append(doc_copy)

        print(f"✅ Đã thêm {len(documents)} documents")
        print(f"📊 Tổng số documents: {self.index.ntotal}")

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = None
    ) -> List[Dict]:
        """
        Tìm kiếm documents tương tự với query

        Args:
            query_embedding: Vector embedding của câu hỏi
            top_k: Số kết quả trả về

        Returns:
            List[Dict]: Danh sách documents [{
                'content': str,
                'metadata': dict,
                'score': float,  # Khoảng cách (càng nhỏ càng giống)
                'similarity': float  # Độ tương đồng (0-1)
            }]
        """
        if self.index.ntotal == 0:
            print("⚠️  Vector store trống!")
            return []

        top_k = top_k or config.TOP_K_RETRIEVAL

        # Reshape query embedding
        query_vector = query_embedding.reshape(1, -1).astype('float32')

        # Tìm kiếm
        distances, indices = self.index.search(
            query_vector, min(top_k, self.index.ntotal))

        # Chuẩn bị kết quả
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.documents):
                doc = self.documents[idx].copy()
                distance = float(distances[0][i])

                # Chuyển distance thành similarity score (0-1)
                # Distance càng nhỏ -> similarity càng cao
                # Sử dụng công thức: similarity = 1 / (1 + distance)
                similarity = 1.0 / (1.0 + distance)

                doc['score'] = distance
                doc['similarity'] = similarity
                doc['rank'] = i + 1

                results.append(doc)

        return results

    def save(self, path: str = None):
        """
        Lưu vector store ra file

        Args:
            path: Đường dẫn lưu (không bao gồm extension)
        """
        save_path = path or self.index_path

        # Tạo thư mục nếu chưa có
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        # Lưu FAISS index
        faiss.write_index(self.index, f"{save_path}.faiss")

        # Lưu documents metadata
        with open(f"{save_path}.pkl", 'wb') as f:
            pickle.dump({
                'documents': self.documents,
                'dimension': self.dimension
            }, f)

        print(f"✅ Đã lưu vector store tại: {save_path}")

    def load(self, path: str = None):
        """
        Load vector store từ file

        Args:
            path: Đường dẫn load (không bao gồm extension)
        """
        load_path = path or self.index_path

        # Check file tồn tại
        if not Path(f"{load_path}.faiss").exists():
            print(f"❌ Không tìm thấy file: {load_path}.faiss")
            return False

        # Load FAISS index
        self.index = faiss.read_index(f"{load_path}.faiss")

        # Load documents metadata
        with open(f"{load_path}.pkl", 'rb') as f:
            data = pickle.load(f)
            self.documents = data['documents']
            self.dimension = data['dimension']

        print(f"✅ Đã load vector store: {self.index.ntotal} documents")
        return True

    def clear(self):
        """Xóa toàn bộ dữ liệu trong vector store"""
        self.index.reset()
        self.documents = []
        print("🗑️  Đã xóa toàn bộ vector store")

    def get_stats(self) -> Dict:
        """Lấy thống kê về vector store"""
        return {
            'total_documents': self.index.ntotal,
            'dimension': self.dimension,
            'index_type': type(self.index).__name__,
            'is_trained': self.index.is_trained
        }


def demo_vector_store():
    """Demo chức năng vector store"""
    print("=" * 60)
    print("DEMO - VECTOR STORE (FAISS)")
    print("=" * 60)

    # Import embedding model
    from backend.rag.embeddings import EmbeddingModel

    # Tạo embedding model
    print("\n1️⃣  Tạo embedding model...")
    embedder = EmbeddingModel(use_vietnamese=False)  # Dùng model nhẹ cho demo

    # Tạo vector store
    print("\n2️⃣  Tạo vector store...")
    vector_store = VectorStore(dimension=embedder.embedding_dim)

    # Tạo documents mẫu
    print("\n3️⃣  Chuẩn bị documents...")
    texts = [
        "Cảm cúm là bệnh do virus, có triệu chứng sốt và đau đầu",
        "Viêm amidan gây đau họng, khó nuốt, cần uống kháng sinh",
        "Đau đầu có thể do căng thẳng, mất ngủ hoặc thiếu nước",
        "Sốt cao trên 39 độ cần đi khám bác sĩ ngay",
        "Uống nhiều nước giúp giảm triệu chứng cảm cúm",
        "Vitamin C tăng cường hệ miễn dịch phòng bệnh",
        "Đau bụng có thể do viêm dạ dày hoặc ngộ độc thực phẩm",
        "Nghỉ ngơi đủ giấc giúp cơ thể phục hồi nhanh",
        "Rửa tay thường xuyên để phòng ngừa vi khuẩn",
        "Tiêm vaccine phòng cúm mỗi năm một lần"
    ]

    documents = []
    for i, text in enumerate(texts, 1):
        documents.append({
            'content': text,
            'metadata': {
                'source': f'doc_{i}.txt',
                'topic': 'sức khỏe',
                'id': i
            }
        })

    # Encode documents
    print(f"⏳ Đang encode {len(documents)} documents...")
    documents = embedder.encode_documents(documents)

    # Thêm vào vector store
    print("\n4️⃣  Thêm documents vào vector store...")
    vector_store.add_documents(documents)

    # Hiển thị thống kê
    stats = vector_store.get_stats()
    print("\n📊 Thống kê:")
    for key, value in stats.items():
        print(f"  - {key}: {value}")

    # Test tìm kiếm
    print("\n5️⃣  TEST TÌM KIẾM")
    print("=" * 60)

    queries = [
        "Làm sao để chữa cảm cúm?",
        "Đau đầu phải làm gì?",
        "Cách phòng bệnh hiệu quả"
    ]

    for query in queries:
        print(f"\n❓ Câu hỏi: '{query}'")

        # Encode query
        query_embedding = embedder.encode_text(query)

        # Tìm kiếm
        results = vector_store.search(query_embedding, top_k=3)

        print("🔍 Top 3 kết quả:")
        for result in results:
            print(f"\n  Rank #{result['rank']}:")
            print(f"  📄 {result['content']}")
            print(f"  📊 Similarity: {result['similarity']:.3f}")
            print(f"  📌 Source: {result['metadata']['source']}")

    # Test save/load
    print("\n6️⃣  TEST SAVE/LOAD")
    print("=" * 60)

    save_path = str(config.VECTOR_STORE_DIR / "demo_index")
    vector_store.save(save_path)

    # Tạo vector store mới và load
    print("\n⏳ Tạo vector store mới và load...")
    new_vector_store = VectorStore(dimension=embedder.embedding_dim)
    new_vector_store.load(save_path)

    # Test search lại
    query_embedding = embedder.encode_text("sốt cao")
    results = new_vector_store.search(query_embedding, top_k=2)

    print("\n✅ Test search sau khi load:")
    for result in results[:2]:
        print(
            f"  - {result['content'][:50]}... (sim: {result['similarity']:.3f})")

    print("\n✅ Demo hoàn tất!")


if __name__ == "__main__":
    demo_vector_store()
