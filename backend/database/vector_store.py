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

# Thêm path để import config từ thư mục gốc của dự án
sys.path.append(str(Path(__file__).parent.parent.parent))

# Lớp VectorStore đóng vai trò là Cơ sở dữ liệu Vector (Vector Database).
# Nhiệm vụ của nó là lưu trữ các đoạn văn bản y khoa đã được "nhúng" (embedding)
# thành các mảng số học nhiều chiều, và thực hiện truy vấn lân cận gần nhất (Nearest Neighbor Search).


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

        # Khởi tạo lõi Index của FAISS.
        # IndexFlatL2 thực hiện tìm kiếm vét cạn (Exhaustive Search) dựa trên
        # khoảng cách Euclidean (L2 Distance). Điều này đảm bảo độ chính xác tuyệt đối (100%)
        # cho tập dữ liệu vừa và nhỏ (như 40 tài liệu y khoa của dự án) thay vì dùng các thuật toán xấp xỉ (ANN).
        self.index = faiss.IndexFlatL2(dimension)

        # Danh sách (List) dùng để ánh xạ (Mapping) từ chỉ mục (Index) của FAISS
        # ngược trở lại nội dung văn bản gốc và siêu dữ liệu (Metadata) tương ứng.
        self.documents = []

        print(f"Khoi tao Vector Store (dimension={dimension})")

    def add_documents(self, documents: List[Dict]):
        """
        Thêm documents vào vector store

        Args:
            documents: List[{'content': str, 'metadata': dict, 'embedding': np.ndarray}]
        """
        if not documents:
            print("Khong co document nao de them")
            return

        # Trích xuất toàn bộ mảng embedding và chuyển thành ma trận numpy 2 chiều (2D array)
        embeddings = np.array([doc['embedding'] for doc in documents])

        # Tiền kiểm tra (Sanity Check) số chiều của vector đầu vào.
        # Đảm bảo vector sinh ra từ Embedding Model (vd: 384 chiều) khớp với cấu trúc của FAISS Index.
        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Embedding dimension khong khop! "
                f"Expected {self.dimension}, got {embeddings.shape[1]}"
            )

        # Đẩy dữ liệu vào FAISS. Bắt buộc phải ép kiểu về 'float32' vì kiến trúc của thư viện
        # FAISS (được viết bằng C++) được tối ưu hóa ở mức phần cứng cho kiểu dữ liệu này.
        self.index.add(embeddings.astype('float32'))

        # Lưu trữ song song siêu dữ liệu (Metadata) và nội dung (Content)
        # theo đúng thứ tự Index mà FAISS vừa lưu để có thể trích xuất lại sau này.
        for doc in documents:
            doc_copy = {
                'content': doc['content'],
                'metadata': doc.get('metadata', {})
            }
            self.documents.append(doc_copy)

        print(f"Da them {len(documents)} documents")
        print(f"Tong so documents: {self.index.ntotal}")

    # Hàm thực thi quá trình Truy xuất Ngữ nghĩa (Semantic Retrieval)
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
            print("Vector store trong!")
            return []

        top_k = top_k or config.TOP_K_RETRIEVAL

        # Định dạng lại kích thước (Reshape) vector câu hỏi thành ma trận [1, N_Dimensions]
        # Đây là quy định bắt buộc của giao diện lập trình FAISS.
        query_vector = query_embedding.reshape(1, -1).astype('float32')

        # Gọi thuật toán k-Nearest Neighbors (k-NN) từ thư viện C++ lõi của FAISS.
        # Trả về khoảng cách L2 (distances) và vị trí (indices) của top_k tài liệu gần nhất.
        distances, indices = self.index.search(
            query_vector, min(top_k, self.index.ntotal))

        # Chuẩn bị danh sách kết quả trả về cho hệ thống (RAG Pipeline)
        results = []
        for i, idx in enumerate(indices[0]):
            # Kiểm tra biên an toàn (Boundary Check)
            if idx < len(self.documents):
                doc = self.documents[idx].copy()
                distance = float(distances[0][i])

                # Thuật toán chuẩn hóa điểm số (Score Normalization).
                # Vì khoảng cách L2 có dải giá trị từ [0, +vô cực] (khoảng cách càng nhỏ càng giống nhau),
                # ta dùng phép nghịch đảo 1/(1+d) để quy đổi điểm số về dải [0, 1] cho dễ cấu hình Threshold.
                similarity = 1.0 / (1.0 + distance)

                doc['score'] = distance
                doc['similarity'] = similarity
                doc['rank'] = i + 1

                results.append(doc)

        return results

    # Hàm tuần tự hóa (Serialization) dữ liệu từ RAM xuống ổ cứng (Disk)
    def save(self, path: str = None):
        """
        Lưu vector store ra file

        Args:
            path: Đường dẫn lưu (không bao gồm extension)
        """
        save_path = path or self.index_path

        # Tự động tạo cây thư mục nếu nó chưa tồn tại trên hệ điều hành
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        # Xuất cấu trúc Index nhị phân của FAISS ra file .faiss
        faiss.write_index(self.index, f"{save_path}.faiss")

        # Sử dụng thư viện Pickle của Python để lưu cấu trúc đối tượng (List of Dicts)
        # chứa Metadata và Text gốc ra một file nhị phân riêng biệt (.pkl)
        with open(f"{save_path}.pkl", 'wb') as f:
            pickle.dump({
                'documents': self.documents,
                'dimension': self.dimension
            }, f)

        print(f"Da luu vector store tai: {save_path}")

    # Hàm nạp dữ liệu (Deserialization) từ ổ cứng lên RAM khi khởi động Server Flask
    def load(self, path: str = None):
        """
        Load vector store từ file

        Args:
            path: Đường dẫn load (không bao gồm extension)
        """
        load_path = path or self.index_path

        # Kiểm tra tính toàn vẹn của file (File Integrity Check)
        if not Path(f"{load_path}.faiss").exists():
            print(f"Khong tim thay file: {load_path}.faiss")
            return False

        # Khôi phục đối tượng FAISS Index
        self.index = faiss.read_index(f"{load_path}.faiss")

        # Khôi phục dữ liệu Metadata
        with open(f"{load_path}.pkl", 'rb') as f:
            data = pickle.load(f)
            self.documents = data['documents']
            self.dimension = data['dimension']

        print(f"Da load vector store: {self.index.ntotal} documents")
        return True

    def clear(self):
        """Xóa toàn bộ dữ liệu trong vector store"""
        self.index.reset()
        self.documents = []
        print("Da xoa toan bo vector store")

    def get_stats(self) -> Dict:
        """Lấy thống kê về vector store"""
        return {
            'total_documents': self.index.ntotal,
            'dimension': self.dimension,
            'index_type': type(self.index).__name__,
            'is_trained': self.index.is_trained
        }

# Khối lệnh kiểm thử đơn vị (Unit Test) chạy độc lập để đánh giá mô hình Vector Store


def demo_vector_store():
    """Demo chức năng vector store"""
    print("=" * 60)
    print("DEMO - VECTOR STORE (FAISS)")
    print("=" * 60)

    # Import embedding model
    from backend.rag.embeddings import EmbeddingModel

    # Tạo embedding model
    print("\n Tao embedding model...")
    embedder = EmbeddingModel(use_vietnamese=False)  # Dùng model nhẹ cho demo

    # Tạo vector store
    print("\n Tao vector store...")
    vector_store = VectorStore(dimension=embedder.embedding_dim)

    # Tạo documents mẫu
    print("\n Chuan bi documents...")
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
    print(f" Dang encode {len(documents)} documents...")
    documents = embedder.encode_documents(documents)

    # Thêm vào vector store
    print("\n Them documents vao vector store...")
    vector_store.add_documents(documents)

    # Hiển thị thống kê
    stats = vector_store.get_stats()
    print("\n Thong ke:")
    for key, value in stats.items():
        print(f"  - {key}: {value}")

    # Test tìm kiếm
    print("\n TEST TIM KIEM")
    print("=" * 60)

    queries = [
        "Làm sao để chữa cảm cúm?",
        "Đau đầu phải làm gì?",
        "Cách phòng bệnh hiệu quả"
    ]

    for query in queries:
        print(f"\n Cau hoi: '{query}'")

        # Encode query
        query_embedding = embedder.encode_text(query)

        # Tìm kiếm
        results = vector_store.search(query_embedding, top_k=3)

        print(" Top 3 ket qua:")
        for result in results:
            print(f"\n  Rank #{result['rank']}:")
            print(f"   {result['content']}")
            print(f"   Similarity: {result['similarity']:.3f}")
            print(f"   Source: {result['metadata']['source']}")

    # Test save/load
    print("\n TEST SAVE/LOAD")
    print("=" * 60)

    save_path = str(config.VECTOR_STORE_DIR / "demo_index")
    vector_store.save(save_path)

    # Tạo vector store mới và load
    print("\n Tao vector store moi va load...")
    new_vector_store = VectorStore(dimension=embedder.embedding_dim)
    new_vector_store.load(save_path)

    # Test search lại
    query_embedding = embedder.encode_text("sốt cao")
    results = new_vector_store.search(query_embedding, top_k=2)

    print("\n Test search sau khi load:")
    for result in results[:2]:
        print(
            f"  - {result['content'][:50]}... (sim: {result['similarity']:.3f})")

    print("\n Demo hoan tat!")


if __name__ == "__main__":
    demo_vector_store()
