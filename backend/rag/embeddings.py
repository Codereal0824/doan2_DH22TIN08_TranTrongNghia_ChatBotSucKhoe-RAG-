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
import hashlib

# Thêm path để import config
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import logger

logger = get_logger(__name__)


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
            # Chọn model dựa trên ngôn ngữ
            if use_vietnamese:
                self.model_name = config.EMBEDDING_MODEL_VI
                logger.info(f"🇻🇳 Sử dụng model tiếng Việt: {self.model_name}")
            else:
                self.model_name = config.EMBEDDING_MODEL
                logger.info(f"🌍 Sử dụng model đa ngôn ngữ: {self.model_name}")

        logger.info("⏳ Đang tải model embedding...")
        try:
            self.model = SentenceTransformer(self.model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(
                f"✅ Model đã sẵn sàng! (Dimension: {self.embedding_dim})")
        except Exception as e:
            logger.error(f"❌ Lỗi tải model: {e}")
            logger.info("💡 Thử dùng model backup...")
            # Fallback về model nhẹ hơn
            self.model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            self.model = SentenceTransformer(self.model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"✅ Đã tải model backup: {self.model_name}")

        # Initialize cache stats manual track if wanted, but lru_cache provides cache_info()
        self._cache_hits = 0
        self._cache_misses = 0
        # text → np.ndarray (instance-level, no memory leak)
        self._embedding_cache: dict = {}

    def _compute_embedding(self, text: str) -> np.ndarray:
        """Cache embedding theo text, tránh dùng lru_cache trên instance method."""
        if text in self._embedding_cache:
            self._cache_hits += 1
            return self._embedding_cache[text]
        self._cache_misses += 1
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
        if not text or not text.strip():
            return np.zeros(self.embedding_dim)

        embedding = self._compute_embedding(text)
        logger.debug(
            f"🎯 Cache stats — hits: {self._cache_hits}, misses: {self._cache_misses}")
        return embedding

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

        # Loại bỏ text rỗng
        valid_texts = [
            text if text and text.strip() else " " for text in texts]

        embeddings = self.model.encode(
            valid_texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )

        return embeddings

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

        # Lấy content
        contents = [doc.get('content', '') for doc in documents]

        # Encode batch
        print(f"⏳ Đang encode {len(contents)} documents...")
        embeddings = self.encode_batch(contents, show_progress=True)

        # Gắn embedding vào documents
        for i, doc in enumerate(documents):
            doc['embedding'] = embeddings[i]

        print(f"✅ Đã encode {len(documents)} documents!")
        return documents

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

        # Cosine similarity
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


def demo_embeddings():
    """Demo chức năng embedding"""
    print("=" * 60)
    print("DEMO - TEXT EMBEDDINGS")
    print("=" * 60)

    # Tạo embedding model
    embedder = EmbeddingModel(use_vietnamese=True)

    # Hiển thị info
    info = embedder.get_model_info()
    print(f"\n📊 Thông tin model:")
    print(f"  - Model: {info['model_name']}")
    print(f"  - Dimension: {info['embedding_dimension']}")
    print(f"  - Max sequence length: {info['max_seq_length']}")

    # Test encode một văn bản
    print("\n" + "=" * 60)
    print("TEST 1 - ENCODE ĐƠN")
    print("=" * 60)

    text = "Đau đầu có thể do căng thẳng hoặc mất ngủ"
    embedding = embedder.encode_text(text)

    print(f"Văn bản: '{text}'")
    print(f"Embedding shape: {embedding.shape}")
    print(f"Embedding (10 số đầu): {embedding[:10]}")

    # Test encode nhiều văn bản
    print("\n" + "=" * 60)
    print("TEST 2 - ENCODE BATCH")
    print("=" * 60)

    texts = [
        "Triệu chứng cảm cúm bao gồm sốt và đau đầu",
        "Nghỉ ngơi và uống nhiều nước khi bị cảm",
        "Vitamin C giúp tăng cường hệ miễn dịch",
        "Đau bụng có thể do ăn uống không hợp lý"
    ]

    embeddings = embedder.encode_batch(texts, show_progress=False)
    print(f"Số văn bản: {len(texts)}")
    print(f"Embeddings shape: {embeddings.shape}")

    # Test similarity
    print("\n" + "=" * 60)
    print("TEST 3 - ĐỘ TƯƠNG ĐỒNG")
    print("=" * 60)

    query = "Làm sao để điều trị cảm cúm?"

    print(f"Câu hỏi: '{query}'")
    print(f"\nĐộ tương đồng với các câu khác:")

    for text in texts:
        sim = embedder.similarity(query, text)
        print(f"  - [{sim:.3f}] {text}")

    # Test encode documents
    print("\n" + "=" * 60)
    print("TEST 4 - ENCODE DOCUMENTS")
    print("=" * 60)

    documents = [
        {
            'content': 'Cảm cúm là bệnh do virus gây ra',
            'metadata': {'source': 'doc1.pdf', 'page': 1}
        },
        {
            'content': 'Sốt cao là triệu chứng của cảm cúm',
            'metadata': {'source': 'doc2.pdf', 'page': 5}
        }
    ]

    docs_with_embeddings = embedder.encode_documents(documents)

    print(f"\nKết quả:")
    for i, doc in enumerate(docs_with_embeddings, 1):
        print(f"Document {i}:")
        print(f"  Content: {doc['content']}")
        print(f"  Metadata: {doc['metadata']}")
        print(f"  Embedding shape: {doc['embedding'].shape}")

    print("\n✅ Demo hoàn tất!")


if __name__ == "__main__":
    demo_embeddings()
