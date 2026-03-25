"""
Embeddings - Chuyển đổi văn bản thành vector embeddings (với caching)
"""
from backend.utils.logger import get_logger
from config.config import config
from typing import List
from sentence_transformers import SentenceTransformer
import numpy as np
import sys
from pathlib import Path

# Thêm path để import config
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import logger
logger = get_logger(__name__)

# Lớp EmbeddingModel đóng vai trò là Trình bao bọc (Wrapper) cho thư viện SentenceTransformers.
# Nó chịu trách nhiệm biến đổi văn bản ngôn ngữ tự nhiên thành một không gian vector đa chiều,
# là nền tảng cho công nghệ tìm kiếm ngữ nghĩa (Semantic Search) trong RAG.


class EmbeddingModel:
    """Class quản lý embedding model với caching"""

    def __init__(self, model_name: str = None, use_vietnamese: bool = True):
        """
        Khởi tạo embedding model

        Args:
            model_name: Tên model (nếu None sẽ dùng từ config)
            use_vietnamese: True = dùng model tiếng Việt, False = model tiếng Anh
        """
        if model_name:
            self.model_name = model_name
        else:
            # Lựa chọn mô hình linh hoạt dựa trên cấu hình ngôn ngữ.
            # Việc sử dụng mô hình chuyên biệt cho tiếng Việt (như phobert-base)
            # giúp cải thiện đáng kể độ chính xác khi đối sánh các thuật ngữ y khoa.
            if use_vietnamese:
                self.model_name = config.EMBEDDING_MODEL_VI
                logger.info(f"Su dung model tieng Viet: {self.model_name}")
            else:
                self.model_name = config.EMBEDDING_MODEL
                logger.info(f"Su dung model da ngon ngu: {self.model_name}")

        logger.info("Dang tai model embedding...")
        try:
            # Khởi tạo mô hình học sâu. Trọng số (weights) của mô hình sẽ được tải lên RAM/VRAM.
            self.model = SentenceTransformer(self.model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(
                f"Model da san sang! (Dimension: {self.embedding_dim})")
        except Exception as e:
            # Cơ chế Dự phòng (Fallback Mechanism) tự động.
            # Nếu mô hình chính gặp lỗi (do thiếu tài nguyên mạng hoặc lỗi file),
            # hệ thống sẽ tự động chuyển sang mô hình MiniLM đa ngôn ngữ nhẹ hơn.
            logger.error(f"Loi tai model: {e}")
            logger.info("Thu dung model backup...")

            self.model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            self.model = SentenceTransformer(self.model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Da tai model backup: {self.model_name}")

        # Khởi tạo cơ chế Bộ nhớ đệm (Caching).
        # Thay vì dùng decorator @lru_cache của Python (dễ gây rò rỉ bộ nhớ - Memory Leak khi dùng trên instance method),
        # ta thiết kế một dictionary nội bộ để lưu vết các câu đã được tính toán vector.
        self._cache_hits = 0
        self._cache_misses = 0
        # Cấu trúc: text (str) -> np.ndarray (vector)
        self._embedding_cache: dict = {}

    def _compute_embedding(self, text: str) -> np.ndarray:
        """Cache embedding theo text, tránh dùng lru_cache trên instance method."""
        # Nếu câu hỏi đã tồn tại trong bộ đệm (Cache Hit), trả về ngay vector đã lưu.
        if text in self._embedding_cache:
            self._cache_hits += 1
            return self._embedding_cache[text]

        # Nếu là câu hỏi mới (Cache Miss), yêu cầu mô hình học sâu thực hiện encode.
        self._cache_misses += 1
        # Ép kiểu dữ liệu về Numpy Array thay vì PyTorch Tensor để tương thích trực tiếp với FAISS.
        result = self.model.encode(text, convert_to_numpy=True)
        self._embedding_cache[text] = result
        return result

    def encode_text(self, text: str) -> np.ndarray:
        """
        Chuyển văn bản thành vector embedding (với caching)

        Args:
            text: Văn bản cần encode

        Returns:
            numpy.ndarray: Vector embedding
        """
        # Xử lý các trường hợp ngoại lệ (Edge Cases) như chuỗi rỗng hoặc khoảng trắng,
        # tránh việc mô hình sinh ra vector rác (Noise) làm nhiễu không gian tìm kiếm.
        if not text or not text.strip():
            return np.zeros(self.embedding_dim)

        embedding = self._compute_embedding(text)
        logger.debug(
            f"Cache stats - hits: {self._cache_hits}, misses: {self._cache_misses}")
        return embedding

    # Hàm mã hóa theo Lô (Batch Processing).
    # Việc đẩy một mảng lớn dữ liệu vào mô hình học sâu cùng lúc sẽ tối ưu hóa sức mạnh của CPU/GPU
    # thông qua việc song song hóa các phép tính ma trận, nhanh hơn nhiều so với việc chạy vòng lặp for.
    def encode_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> np.ndarray:
        """
        Chuyển nhiều văn bản thành vectors (nhanh hơn encode từng cái)

        Args:
            texts: Danh sách văn bản
            batch_size: Số văn bản xử lý cùng lúc
            show_progress: Hiển thị progress bar

        Returns:
            numpy.ndarray: Ma trận embeddings (n_texts, embedding_dim)
        """
        if not texts:
            return np.array([])

        # Tiền xử lý dữ liệu: Thay thế các đoạn văn bản rỗng bằng một khoảng trắng an toàn
        # để hàm encode của SentenceTransformer không văng lỗi.
        valid_texts = [
            text if text and text.strip() else " " for text in texts]

        embeddings = self.model.encode(
            valid_texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )

        return embeddings

    # Hàm tiện ích đóng gói dữ liệu dành riêng cho việc lập chỉ mục tài liệu ngoại tuyến (Offline Indexing).
    def encode_documents(self, documents: List[dict]) -> List[dict]:
        """
        Encode danh sách documents (với metadata)

        Args:
            documents: List[{'content': str, 'metadata': dict}]

        Returns:
            List[{'content': str, 'metadata': dict, 'embedding': np.ndarray}]
        """
        if not documents:
            return []

        # Tách riêng phần nội dung văn bản (content) để đẩy vào mô hình
        contents = [doc.get('content', '') for doc in documents]

        print(f"Dang encode {len(contents)} documents...")
        embeddings = self.encode_batch(contents, show_progress=True)

        # Gắn (Inject) vector đã được tính toán trở lại vào từ điển tài liệu,
        # sẵn sàng để được nạp vào cơ sở dữ liệu FAISS.
        for i, doc in enumerate(documents):
            doc['embedding'] = embeddings[i]

        print(f"Da encode {len(documents)} documents!")
        return documents

    # Hàm đo lường mức độ tương đồng giữa hai vector bằng công thức Cosine Similarity.
    # Hàm này dùng để phân tích chéo hoặc gỡ lỗi (Debugging) thủ công, không dùng trực tiếp trong RAG
    # (vì RAG đang dùng khoảng cách L2 Distance của FAISS).
    def similarity(self, text1: str, text2: str) -> float:
        """
        Tính độ tương đồng giữa 2 văn bản (cosine similarity)

        Args:
            text1: Văn bản thứ nhất
            text2: Văn bản thứ hai

        Returns:
            float: Điểm tương đồng (0-1)
        """
        emb1 = self.encode_text(text1)
        emb2 = self.encode_text(text2)

        # Công thức Tích vô hướng (Dot Product) chia cho tích độ dài (Norms) của 2 vector.
        # Điểm số tiến gần về 1 có nghĩa là hai văn bản có chung một chủ đề (semantic meaning).
        similarity = np.dot(emb1, emb2) / \
            (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)

    def get_model_info(self) -> dict:
        """Lấy thông tin về model"""
        return {
            'model_name': self.model_name,
            'embedding_dimension': self.embedding_dim,
            'max_seq_length': self.model.max_seq_length
        }
