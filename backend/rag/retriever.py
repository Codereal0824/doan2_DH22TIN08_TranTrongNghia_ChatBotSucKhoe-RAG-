"""
RAG Retriever - Hybrid Search với Dense (FAISS) + Sparse (BM25) + RRF
"""
from config.config import config
from backend.rag.embeddings import EmbeddingModel
from backend.database.vector_store import VectorStore
from backend.utils.query_normalizer import normalize_query
from backend.utils.logger import get_logger
import sys
from pathlib import Path
from typing import List, Dict
from rank_bm25 import BM25Okapi
import re

logger = get_logger(__name__)

# ============================================
# QUERY INTENT DETECTION (REQUIREMENT 2: SMART RETRIEVAL)
# ============================================


class QueryIntent:
    """Phát hiện intent của query để tối ưu retrieval"""

    # Intent patterns for Vietnamese health queries
    INTENT_PATTERNS = {
        'symptom': [
            r'triệu chứng',
            r'dấu hiệu',
            r'biểu hiện',
            r'có triệu chứng gì',
            r'có dấu hiệu gì',
            r'nhận biết',
            r'phát hiện'
        ],
        'cause': [
            r'nguyên nhân',
            r'tại sao',
            r'vì sao',
            r'do đâu',
            r'gây ra bởi',
            r'yếu tố nguy cơ'
        ],
        'prevention': [
            r'phòng ngừa',
            r'phòng tránh',
            r'phòng bệnh',
            r'cách phòng',
            r'biện pháp phòng',
            r'dự phòng'
        ],
        'treatment': [
            r'điều trị',
            r'chữa',
            r'chăm sóc',
            r'xử lý',
            r'hỗ trợ',
            r'làm sao để'
        ],
        'when_to_see_doctor': [
            r'khi nào cần',
            r'khi nào nên',
            r'khi nào phải',
            r'đi bác sĩ',
            r'đi khám',
            r'cần khám'
        ],
        'comparison': [
            r'khác nhau',
            r'giống nhau',
            r'so sánh',
            r'phân biệt',
            r'và .+ có .+ giống',
            r'có giống'
        ],
        'disease_from_symptom': [
            r'là .+ của bệnh gì',
            r'là bệnh gì',
            r'mắc bệnh gì',
            r'bị bệnh gì',
            r'liên quan đến bệnh'
        ]
    }

    # Section keywords to boost based on intent
    SECTION_BOOST = {
        'symptom': ['dấu hiệu', 'triệu chứng', 'biểu hiện', 'nhận biết'],
        'cause': ['nguyên nhân', 'yếu tố nguy cơ', 'tại sao', 'do đâu'],
        'prevention': ['phòng ngừa', 'phòng tránh', 'biện pháp', 'dự phòng'],
        'treatment': ['điều trị', 'chữa', 'chăm sóc', 'hỗ trợ', 'xử lý'],
        'when_to_see_doctor': ['khi nào', 'cần khám', 'đi bác sĩ', 'cơ sở y tế']
    }

    @staticmethod
    def detect_intent(query: str) -> List[str]:
        """Phát hiện intent từ query (có thể có nhiều intent)

        Args:
            query: Câu hỏi

        Returns:
            List[str]: Danh sách intent detected
        """
        query_lower = query.lower()
        detected_intents = []

        for intent_type, patterns in QueryIntent.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    detected_intents.append(intent_type)
                    break  # Found intent, move to next type

        return detected_intents if detected_intents else ['general']

    @staticmethod
    def get_section_keywords(intents: List[str]) -> List[str]:
        """Lấy keywords để boost sections dựa trên intent

        Args:
            intents: Danh sách intent

        Returns:
            List[str]: Keywords để boost
        """
        keywords = []
        for intent in intents:
            if intent in QueryIntent.SECTION_BOOST:
                keywords.extend(QueryIntent.SECTION_BOOST[intent])
        return list(set(keywords))  # Remove duplicates


# ============================================
# DISEASE-SPECIFIC KEYWORD BOOSTING (TASK 3)
# ============================================

class DiseaseDetector:
    """Detect specific diseases in query for targeted retrieval"""

    # Disease name to filename mapping
    # QUAN TRỌNG: Cụm từ DÀI HƠN phải đứng trước cụm ngắn hơn trong dict
    # vì detect_diseases duyệt theo thứ tự và dừng khi khớp
    DISEASE_TO_FILE = {
        # ── Cụm dài/cụ thể trước ──────────────────────────────────
        'viêm họng kích ứng': 'viem_hong_kich_ung.txt',
        'viêm họng cấp': 'viem_hong_cap.txt',
        'viêm mũi dị ứng': 'viem_mui_di_ung.txt',
        'viêm da cơ địa': 'viem_da_co_dia.txt',
        'viêm kết mạc': 'viem_ket_mac.txt',
        'đau mắt đỏ': 'viem_ket_mac.txt',
        'mắt đỏ': 'viem_ket_mac.txt',
        'khô mắt': 'Kho_mat.txt',
        'hội chứng u nang buồng trứng': 'hoi_chung_u_nan_buong_trung.txt',
        'u nang buồng trứng': 'hoi_chung_u_nan_buong_trung.txt',
        'sốt xuất huyết': 'sot_xuat_huyet.txt',
        'dengue': 'sot_xuat_huyet.txt',
        'cúm mùa': 'cum_mua.txt',
        'cảm cúm': 'cam_lanh.txt',
        'cảm lạnh': 'cam_lanh.txt',
        'đái tháo đường': 'dai_thao_duong.txt',
        'tiểu đường': 'dai_thao_duong.txt',
        'diabetes': 'dai_thao_duong.txt',
        'tăng huyết áp': 'tang_huyet_ap.txt',
        'cao huyết áp': 'tang_huyet_ap.txt',
        'huyết áp cao': 'tang_huyet_ap.txt',
        'rối loạn lo âu': 'roi_loan_lo_au.txt',
        'lo âu': 'roi_loan_lo_au.txt',
        'rối loạn tiêu hóa': 'roi_loan_tieu_hoa.txt',
        'hen phế quản': 'hen_phe_quan.txt',
        'hen suyễn': 'hen_phe_quan.txt',
        'viêm gan b': 'viem_gan_B.txt',
        'thoái hóa khớp': 'thoai_hoa_khop_goi.txt',
        'thoái hóa khớp gối': 'thoai_hoa_khop_goi.txt',
        'sức khỏe tâm thần': 'suc_khoe_tam_than.txt',
        'nhiễm trùng đường tiết niệu': 'nhiem_trung_duong_tiet_nieu.txt',
        'tiết niệu': 'nhiem_trung_duong_tiet_nieu.txt',
        'suy dinh dưỡng': 'suy_dinh_duong.txt',
        'dinh dưỡng': 'suy_dinh_duong.txt',
        'còi xương': 'coi_xuong.txt',
        'đau bụng kinh': 'dau_bung_kinh.txt',
        'bụng kinh': 'dau_bung_kinh.txt',
        'mụn trứng cá': 'mun_trung_ca.txt',
        'bệnh tim mạch': 'benh_tim_mach.txt',
        'tim mạch': 'benh_tim_mach.txt',
        'lười vận động': 'luoi_van_dong.txt',
        'vận động': 'luoi_van_dong.txt',
        'tiêm chủng': 'tiem_chung.txt',
        'vaccine': 'tiem_chung.txt',
        'sỏi thận': 'soi_than.txt',
        'suy giáp': 'suy_giap.txt',
        'béo phì': 'beo_phi_do_loi_song.txt',
        'covid-19': 'Covid19.txt',
        'covid19': 'Covid19.txt',
        'ung thư': 'ung_thu.txt',
        'trầm cảm': 'tram_cam.txt',
        'đau lưng': 'Dau_lung.txt',
        'say nắng': 'say_nang.txt',
        'mất nước': 'mat_nuoc.txt',
        'mất ngủ': 'mat_ngu.txt',
        'khó ngủ': 'mat_ngu.txt',
        'táo bón': 'tao_bon_chuc_nang.txt',
        'bệnh gút': 'Gout.txt',
        # ── Cụm ngắn sau (tránh match sớm) ───────────────────────
        'viêm xoang': 'viem_xoang.txt',
        'xoang': 'viem_xoang.txt',
        'viêm họng': 'viem_hong_cap.txt',
        'viêm mũi': 'viem_mui_di_ung.txt',
        'viêm gan': 'viem_gan_B.txt',
        'gout': 'Gout.txt',
        'stress': 'stress.txt',
        'căng thẳng': 'stress.txt',
        'ho': 'ho_thong_thuong.txt',
        'covid': 'Covid19.txt',
        'hen': 'hen_phe_quan.txt',
        'cúm': 'cum_mua.txt',
        'influenza': 'cum_mua.txt',
        # ── Symptom combination keywords ─────────────────────────
        # Cho phép detect dựa trên combo triệu chứng đặc trưng của bệnh
        'chóng mặt': 'sot_xuat_huyet.txt',  # sốt xuất huyết hay có chóng mặt
        'phát ban': 'sot_xuat_huyet.txt',
        'xuất huyết': 'sot_xuat_huyet.txt',
        'đau khớp': 'Gout.txt',
        'đau xương': 'sot_xuat_huyet.txt',
        'mệt mỏi': 'stress.txt',
        'lo lắng': 'roi_loan_lo_au.txt',
        'mất ngủ': 'mat_ngu.txt',
    }

    @staticmethod
    def detect_diseases(query: str) -> List[str]:
        """Detect disease keywords in query and return target filenames

        Args:
            query: User query

        Returns:
            List[str]: Target filenames to boost
        """
        query_lower = query.lower()
        target_files = []

        # Sắp xếp theo độ dài keyword giảm dần để cụm dài (cụ thể hơn) khớp trước
        # Ví dụ: "viêm họng kích ứng" khớp trước "viêm họng" với cùng query
        sorted_keywords = sorted(
            DiseaseDetector.DISEASE_TO_FILE.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )

        matched_spans = []  # Theo dõi vị trí đã khớp để tránh khớp chồng chéo

        for disease_keyword, filename in sorted_keywords:
            idx = query_lower.find(disease_keyword)
            if idx == -1:
                continue

            # Kiểm tra xem vị trí này có bị chồng lên khớp dài hơn không
            span = (idx, idx + len(disease_keyword))
            overlaps = any(
                not (span[1] <= s[0] or span[0] >= s[1])
                for s in matched_spans
            )
            if overlaps:
                continue  # Bỏ qua cụm ngắn nếu đã có cụm dài khớp ở cùng vị trí

            matched_spans.append(span)
            if filename not in target_files:
                target_files.append(filename)

        return target_files


# Import modules
sys.path.append(str(Path(__file__).parent.parent.parent))


class RAGRetriever:
    """
    Hybrid Retriever: Dense (FAISS) + Sparse (BM25) + RRF

    Sử dụng Reciprocal Rank Fusion để kết hợp điểm từ:
    - Dense Retrieval: FAISS vector search (semantic similarity)
    - Sparse Retrieval: BM25 keyword matching (lexical similarity)
    """

    def __init__(
        self,
        vector_store: VectorStore = None,
        embedder: EmbeddingModel = None,
        top_k: int = None
    ):
        """
        Khởi tạo Hybrid Retriever

        Args:
            vector_store: Vector store instance (nếu None sẽ tạo mới)
            embedder: Embedding model (nếu None sẽ tạo mới)
            top_k: Số documents trả về
        """
        self.top_k = top_k or config.TOP_K_RETRIEVAL

        # Khởi tạo embedder (Dense Retrieval)
        if embedder:
            self.embedder = embedder
        else:
            if config.DEBUG:
                logger.debug("⏳ Đang khởi tạo Embedding Model...")
            self.embedder = EmbeddingModel(use_vietnamese=True)

        # Khởi tạo vector store (Dense Retrieval)
        if vector_store:
            self.vector_store = vector_store
        else:
            if config.DEBUG:
                logger.debug("⏳ Đang khởi tạo Vector Store...")
            self.vector_store = VectorStore(
                dimension=self.embedder.embedding_dim)
            self.load_vector_store()

        # ============================================
        # BM25 SPARSE RETRIEVAL (NEW)
        # ============================================
        # Corpus: danh sách documents để build BM25 index
        self.bm25_corpus = []  # List[List[str]] - tokenized documents
        self.bm25_model = None  # BM25Okapi instance
        self._build_bm25_index()

        if config.DEBUG:
            logger.info(f"✅ Hybrid Retriever sẵn sàng! (Top-K: {self.top_k})")
            logger.info(
                f"   Dense: FAISS ({self.vector_store.index.ntotal} docs)")
            logger.info(f"   Sparse: BM25 ({len(self.bm25_corpus)} docs)")

    def _tokenize_text(self, text: str) -> List[str]:
        """
        Tokenize text cho BM25 (simple whitespace splitting)

        Args:
            text: Input text

        Returns:
            List[str]: Danh sách tokens
        """
        # Simple tokenization: lowercase + split by whitespace
        return text.lower().split()

    def _build_bm25_index(self):
        """
        Build BM25 index từ documents trong vector store

        Gọi sau khi load vector store để đồng bộ corpus
        """
        if not hasattr(self.vector_store, 'documents') or not self.vector_store.documents:
            logger.warning(
                "⚠️  Vector store chưa có documents, bỏ qua BM25 indexing")
            self.bm25_corpus = []
            self.bm25_model = None
            return

        logger.info("🔨 Đang build BM25 index...")

        # Tokenize tất cả documents
        self.bm25_corpus = [
            self._tokenize_text(doc.get('content', ''))
            for doc in self.vector_store.documents
        ]

        # Build BM25 model
        self.bm25_model = BM25Okapi(self.bm25_corpus)

        logger.info(
            f"✅ BM25 index đã sẵn sàng: {len(self.bm25_corpus)} documents")

    def _extract_disease_keywords(self, query: str) -> List[str]:
        """Backward-compatible disease keyword extraction for legacy tests/callers.

        Returns matched disease phrases from query text (not filenames).
        """
        if not query:
            return []

        query_lower = query.lower()
        matched_keywords = []
        matched_spans = []

        # Match longer phrases first to avoid short-keyword shadowing.
        sorted_keywords = sorted(
            DiseaseDetector.DISEASE_TO_FILE.keys(),
            key=len,
            reverse=True,
        )

        for keyword in sorted_keywords:
            idx = query_lower.find(keyword)
            if idx == -1:
                continue

            span = (idx, idx + len(keyword))
            overlaps = any(
                not (span[1] <= s[0] or span[0] >= s[1])
                for s in matched_spans
            )
            if overlaps:
                continue

            matched_spans.append(span)
            matched_keywords.append(keyword)

        return matched_keywords

    def load_vector_store(self, path: str = None) -> bool:
        """
        Load vector store từ file

        Args:
            path: Đường dẫn (nếu None dùng path mặc định)

        Returns:
            bool: True nếu load thành công
        """
        load_path = path or str(
            config.VECTOR_STORE_DIR / "health_faiss.index")
        success = self.vector_store.load(load_path)

        if success:
            if config.DEBUG:
                logger.debug(
                    f"✅ Đã load vector store: {self.vector_store.index.ntotal} documents")
        else:
            if config.DEBUG:
                logger.debug(
                    "⚠️  Chưa có vector store. Hãy build trước bằng build_rag_pipeline.py")

        return success

    def retrieve(self, query: str, top_k: int = None, apply_threshold: bool = True) -> List[Dict]:
        """
        HYBRID RETRIEVAL với RRF (Reciprocal Rank Fusion) + SMART SECTION BOOSTING

        Pipeline:
        1. Query Intent Detection → Identify user's information need
        2. Dense Retrieval: FAISS semantic search → ranks
        3. Sparse Retrieval: BM25 keyword matching → ranks
        4. Section Boosting: Prioritize sections matching query intent
        5. RRF Fusion: Combine rankings with intent-aware boosting
        6. Re-rank và trả về top-K documents

        Args:
            query: Câu hỏi/query
            top_k: Số documents trả về (nếu None dùng self.top_k)
            apply_threshold: Có áp dụng relevance threshold không

        Returns:
            List[Dict]: Documents với RRF score, sorted by relevance (high → low)
        """
        k = top_k or self.top_k

        # ============================================
        # 1. QUERY INTENT DETECTION (REQUIREMENT 2)
        # ============================================
        detected_intents = QueryIntent.detect_intent(query)
        section_keywords = QueryIntent.get_section_keywords(detected_intents)

        if config.DEBUG:
            logger.debug(f"\n🎯 Detected Intents: {detected_intents}")
            logger.debug(f"📋 Section Keywords: {section_keywords}")

        # ============================================
        # 1.5. DISEASE-SPECIFIC DETECTION (TASK 3)
        # ============================================
        target_diseases = DiseaseDetector.detect_diseases(query)

        if config.DEBUG and target_diseases:
            logger.debug(f"🎯 Target Diseases Detected: {target_diseases}")

        # ============================================
        # 2. QUERY NORMALIZATION
        # ============================================
        normalized_query = normalize_query(query)
        query_for_search = normalized_query if normalized_query else query

        # Query expansion cho dạng "X là dấu hiệu của bệnh gì?" — trích xuất
        # riêng phần triệu chứng để BM25 match rộng hơn trong tài liệu.
        if 'disease_from_symptom' in detected_intents:
            # Loại bỏ phần hỏi, giữ lại triệu chứng thuần
            symptom_part = re.sub(
                r'\s*(là|có thể là|có phải là)?\s*(dấu hiệu|triệu chứng|biểu hiện)?\s*'
                r'(của)?\s*(bệnh gì|bệnh nào|những bệnh gì)[?.]?\s*$',
                '', query_for_search, flags=re.IGNORECASE).strip()
            if symptom_part and symptom_part != query_for_search:
                query_for_search = symptom_part
                if config.DEBUG:
                    logger.debug(
                        f"🔍 Query expanded (symptom only): '{query_for_search}'")

        if config.DEBUG:
            logger.debug(f"\n🔍 Original Query: '{query}'")
            if normalized_query != query.lower().strip():
                logger.debug(f"🔍 Normalized Query: '{query_for_search}'")

        # ============================================
        # 2. DENSE RETRIEVAL (FAISS) - TWO-STAGE APPROACH
        # ============================================
        query_embedding = self.embedder.encode_text(query_for_search)

        # Stage 1: Retrieve more candidates for better recall
        # Use TOP_K_INITIAL (12) to ensure we capture all relevant diseases
        candidate_size = config.TOP_K_INITIAL if hasattr(
            config, 'TOP_K_INITIAL') else max(k * 2, 12)

        if config.DEBUG:
            logger.debug(f"📊 Stage 1: Retrieving {candidate_size} candidates")

        dense_results = self.vector_store.search(
            query_embedding, top_k=candidate_size)

        # Tạo dense ranking: {doc_id: rank} (1-indexed)
        dense_ranks = {}
        for rank, doc in enumerate(dense_results, start=1):
            doc_id = id(doc)  # Unique ID cho document
            dense_ranks[doc_id] = rank
            doc['_doc_id'] = doc_id  # Lưu lại để map sau

        if config.DEBUG:
            logger.debug(
                f"📊 Dense (FAISS): Retrieved {len(dense_results)} candidates")

        # ============================================
        # 3. SPARSE RETRIEVAL (BM25)
        # ============================================
        sparse_ranks = {}
        _bm25_doc_map = {}  # Luôn khởi tạo để tránh NameError khi BM25 chưa sẵn sàng

        if self.bm25_model and self.bm25_corpus:
            # Tokenize query
            query_tokens = self._tokenize_text(query_for_search)

            # BM25 scoring: Calculate scores for all documents
            bm25_scores = self.bm25_model.get_scores(query_tokens)

            # Tạo list (score, doc_index) và sort by score descending
            scored_docs = [(score, idx)
                           for idx, score in enumerate(bm25_scores)]
            scored_docs.sort(reverse=True, key=lambda x: x[0])

            # Lấy top candidate_size và gán ranks
            # Đồng thời lưu lại map doc_id → document để dùng khi build final_results
            _bm25_doc_map = {}
            for rank, (score, doc_idx) in enumerate(scored_docs[:candidate_size], start=1):
                if doc_idx < len(self.vector_store.documents):
                    doc = self.vector_store.documents[doc_idx]
                    doc_id = id(doc)
                    sparse_ranks[doc_id] = rank
                    # Lưu để có thể thêm vào final_results
                    _bm25_doc_map[doc_id] = doc

            if config.DEBUG:
                logger.debug(
                    f"📊 Sparse (BM25): Scored {len(sparse_ranks)} documents")
        else:
            if config.DEBUG:
                logger.warning(
                    "⚠️  BM25 chưa khởi tạo, chỉ dùng Dense retrieval")

        # ============================================
        # 4. RRF FUSION WITH SECTION BOOSTING (REQUIREMENTS 2, 5)
        # ============================================
        rrf_k = config.RRF_K  # Default: 60
        rrf_scores = {}

        # Tính RRF score cho tất cả documents xuất hiện trong dense hoặc sparse
        all_doc_ids = set(dense_ranks.keys()) | set(sparse_ranks.keys())

        # Map doc_id → document cho cả FAISS và BM25 để boost
        _dense_doc_map = {
            doc.get('_doc_id'): doc for doc in dense_results if doc.get('_doc_id')}
        _all_doc_map = {**_dense_doc_map, **_bm25_doc_map}

        for doc_id in all_doc_ids:
            # Nếu không có trong dense → rank rất thấp
            dense_rank = dense_ranks.get(doc_id, 1e9)
            # Nếu không có trong sparse → rank rất thấp
            sparse_rank = sparse_ranks.get(doc_id, 1e9)

            # RRF formula base score
            rrf_score = (1.0 / (rrf_k + dense_rank)) + \
                (1.0 / (rrf_k + sparse_rank))

            # Tìm document từ map tổng hợp (FAISS + BM25)
            doc = _all_doc_map.get(doc_id)

            # ✅ SMART SECTION BOOSTING (REQUIREMENT 2)
            if section_keywords and doc:
                content = doc.get('content', '').lower()
                metadata = doc.get('metadata', {})
                section_title = metadata.get('section_title', '').lower()
                boost_factor = 1.0
                for keyword in section_keywords:
                    if keyword.lower() in section_title or keyword.lower() in content[:200]:
                        boost_factor += 0.15
                if boost_factor > 1.0:
                    rrf_score *= boost_factor
                    if config.DEBUG:
                        logger.debug(
                            f"🎯 Section boost: {boost_factor:.2f}x for {metadata.get('source', 'Unknown')}")

            # ✅ DISEASE-SPECIFIC BOOSTING (TASK 3)
            # Áp dụng cho cả FAISS và BM25-only docs
            if target_diseases and doc:
                source = doc.get('metadata', {}).get('source', '')
                if source in target_diseases:
                    disease_boost = 2.0  # Tăng từ 1.5x lên 2.0x để đảm bảo thắng
                    rrf_score *= disease_boost
                    if config.DEBUG:
                        logger.debug(
                            f"🎯 Disease boost: {disease_boost:.2f}x for {source}")

            rrf_scores[doc_id] = rrf_score

        # ============================================
        # 5. RE-RANK VÀ FORMAT KẾT QUẢ
        # ============================================
        # Tạo final results: FAISS docs + BM25-only docs
        final_results = []
        _added_doc_ids = set()

        # Bước 1: Thêm FAISS docs (có L2 distance)
        for doc in dense_results:
            doc_id = doc.get('_doc_id')
            if doc_id in rrf_scores:
                doc_copy = doc.copy()
                doc_copy['rrf_score'] = rrf_scores[doc_id]
                doc_copy.pop('_doc_id', None)
                doc_copy['dense_score'] = doc.get('score', 999)
                final_results.append(doc_copy)
                _added_doc_ids.add(doc_id)

        # Bước 2: Thêm BM25-only docs (không có trong FAISS top-20)
        # Đây là fix quan trọng: nếu BM25 tìm thấy file liên quan mà FAISS bỏ sót,
        # vẫn đưa vào kết quả với dense_score = 0 để bypass L2 threshold.
        for doc_id, doc in _bm25_doc_map.items():
            if doc_id not in _added_doc_ids and doc_id in rrf_scores:
                doc_copy = doc.copy()
                doc_copy['rrf_score'] = rrf_scores[doc_id]
                doc_copy.pop('_doc_id', None)
                # BM25-only: không có L2 distance → dùng 0.0 để bypass threshold
                doc_copy['dense_score'] = 0.0
                doc_copy['_bm25_only'] = True
                final_results.append(doc_copy)
                if config.DEBUG:
                    src = doc.get('metadata', {}).get('source', 'Unknown')
                    logger.debug(
                        f"➕ BM25-only doc added: {src} (RRF: {rrf_scores[doc_id]:.6f})")

        # Sort by RRF score (descending - higher is better)
        final_results.sort(key=lambda x: x.get('rrf_score', 0), reverse=True)

        if config.DEBUG:
            logger.debug("\n📊 Stage 2: RRF ranked candidates")
            # Show top 10 before filtering
            for i, doc in enumerate(final_results[:10], 1):
                rrf = doc.get('rrf_score', 0)
                dense = doc.get('dense_score', 999)
                source = doc.get('metadata', {}).get('source', 'Unknown')
                logger.debug(
                    f"  [{i}] RRF: {rrf:.6f} | Dense: {dense:.4f} | {source}")

        # ============================================
        # 6. STAGE 3: THRESHOLD FILTERING + CONTEXT DIVERSITY (REQUIREMENTS 5, 9)
        # ============================================
        # Apply L2 distance threshold to filter irrelevant documents
        if apply_threshold:
            # ✅ FIX CRITICAL BUG: Use correct config attribute name
            threshold = config.RELEVANCE_THRESHOLD
            # BM25-only docs bypass L2 threshold (dense_score=0.0 đã đánh dấu)
            filtered = [doc for doc in final_results
                        if doc.get('_bm25_only') or doc.get('dense_score', 999) <= threshold]

            if config.DEBUG:
                logger.debug(
                    f"\n⚡ Stage 3: L2 Threshold Filtering ({threshold})")
                logger.debug(f"✅ Kept: {len(filtered)} docs")
                logger.debug(
                    f"❌ Removed: {len(final_results) - len(filtered)} docs")

            # If no documents pass threshold, return empty
            if not filtered:
                logger.warning("⚠️  No documents passed relevance threshold")
                return []

            # ✅ CONTEXT DIVERSITY VALIDATION (REQUIREMENT 5)
            # Ensure diverse sections: Limit chunks per source
            # Prefer retrieving different sections from same document vs multiple same sections
            final_output = self._apply_diversity_filter(filtered, k)

            if config.DEBUG:
                logger.debug(
                    f"\n🎯 FINAL OUTPUT: Top-{k} documents after diversity filtering")
                for i, doc in enumerate(final_output, 1):
                    rrf = doc.get('rrf_score', 0)
                    dense = doc.get('dense_score', 999)
                    metadata = doc.get('metadata', {})
                    source = metadata.get('source', 'Unknown')
                    section = metadata.get('section_title', 'N/A')
                    logger.debug(
                        f"  [{i}] RRF: {rrf:.6f} | Dense: {dense:.4f} | {source} | {section}")

            return final_output

        # If threshold not applied, return top-k
        return final_results[:k]

    def _apply_diversity_filter(self, docs: List[Dict], max_results: int) -> List[Dict]:
        """Apply diversity filter to prioritize DIFFERENT SOURCES (diseases) over same source

        CRITICAL FIX for PROBLEM 2 & 3:
        - Prioritize retrieving chunks from DIFFERENT diseases/files
        - For symptom queries, we want ALL relevant diseases, not 3 chunks from same disease
        - Example: "sốt và đau đầu" should return chunks from: cum_mua.txt, cam_lanh.txt, 
          sot_xuat_huyet.txt, viem_xoang.txt (4 different diseases)
        - NOT: 3 chunks from cum_mua.txt only

        Args:
            docs: Sorted documents by relevance
            max_results: Maximum number to return

        Returns:
            List[Dict]: Diversified results favoring different sources
        """
        if len(docs) <= max_results:
            return docs

        # Track: source -> list of docs from that source
        source_docs = {}
        for doc in docs:
            source = doc.get('metadata', {}).get('source', 'Unknown')
            if source not in source_docs:
                source_docs[source] = []
            source_docs[source].append(doc)

        selected = []

        # STRATEGY 1: First pass - take 1 chunk from each unique source (prioritize diversity)
        # This ensures we get chunks from ALL relevant diseases
        sources_used = set()
        for doc in docs:
            if len(selected) >= max_results:
                break
            source = doc.get('metadata', {}).get('source', 'Unknown')
            if source not in sources_used:
                selected.append(doc)
                sources_used.add(source)
                if config.DEBUG:
                    logger.debug(f"  ✓ Added first chunk from: {source}")

        # STRATEGY 2: Second pass - add 2nd chunk from sources if space available
        # Only add if it's a DIFFERENT section (not duplicate content)
        if len(selected) < max_results:
            source_sections = {s: set() for s in sources_used}
            for doc in selected:
                source = doc.get('metadata', {}).get('source', 'Unknown')
                section = doc.get('metadata', {}).get('section_title', '')
                source_sections[source].add(section)

            for source in sources_used:
                if len(selected) >= max_results:
                    break
                # Find docs from this source not yet selected
                remaining_docs = [
                    d for d in source_docs[source] if d not in selected]
                for doc in remaining_docs:
                    if len(selected) >= max_results:
                        break
                    section = doc.get('metadata', {}).get('section_title', '')
                    # Only add if different section OR highly relevant
                    if section not in source_sections[source]:
                        selected.append(doc)
                        source_sections[source].add(section)
                        if config.DEBUG:
                            logger.debug(
                                f"  ✓ Added 2nd chunk from: {source} (section: {section})")
                        break

        # STRATEGY 3: Fill remaining slots with highest scoring docs (quality over diversity)
        if len(selected) < max_results:
            remaining = [d for d in docs if d not in selected]
            selected.extend(remaining[:max_results - len(selected)])

        if config.DEBUG:
            sources_count = {}
            for doc in selected:
                source = doc.get('metadata', {}).get('source', 'Unknown')
                sources_count[source] = sources_count.get(source, 0) + 1
            logger.debug(
                f"📊 Diversity filter result: {len(sources_count)} unique sources")
            for source, count in sources_count.items():
                logger.debug(f"  - {source}: {count} chunk(s)")

        return selected

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

        # ✅ FIX: Đổi từ 'similarity' sang 'rrf_score' vì đã chuyển sang thuật toán RRF
        # Filter theo threshold
        filtered = [
            doc for doc in results
            if doc.get('rrf_score', 0) >= similarity_threshold
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
            # ✅ FIX: Đổi từ 'similarity' sang 'rrf_score' và cập nhật format hiển thị
            rrf_score = doc.get('rrf_score', 0)

            context_parts.append(
                f"[Tài liệu {i} - Nguồn: {source} - RRF Score: {rrf_score:.4f}]\n{content}"
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
    print("\n📊 Thống kê Retriever:")
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

        print("\n🔍 Top 3 kết quả:\n")

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
