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
# QUERY INTENT DETECTION (PHÁT HIỆN Ý ĐỊNH TRUY VẤN - BÀI TOÁN TỐI ƯU HÓA)
# ============================================

# Lớp QueryIntent đóng vai trò là một bộ phân loại văn bản (Text Classifier) bằng Regex.
# Trước khi đưa câu hỏi vào không gian Vector, hệ thống sẽ cố gắng hiểu xem người dùng
# đang thực sự muốn hỏi về khía cạnh nào của bệnh (Triệu chứng, Điều trị, Phòng ngừa...).


class QueryIntent:
    """Phát hiện intent của query để tối ưu retrieval"""

    # Cấu trúc từ điển lưu trữ các mẫu biểu thức chính quy (Regex Patterns)
    # được tinh chỉnh (fine-tuned) riêng cho ngữ cảnh y tế tiếng Việt.
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

    # Bảng ánh xạ: Khi đã xác định được Intent, hệ thống sẽ sử dụng các từ khóa này
    # để tăng điểm (Boost) cho các đoạn văn bản (chunks) có tiêu đề (Section) tương ứng.
    SECTION_BOOST = {
        'symptom': ['dấu hiệu', 'triệu chứng', 'biểu hiện', 'nhận biết'],
        'cause': ['nguyên nhân', 'yếu tố nguy cơ', 'tại sao', 'do đâu'],
        'prevention': ['phòng ngừa', 'phòng tránh', 'biện pháp', 'dự phòng'],
        'treatment': ['điều trị', 'chữa', 'chăm sóc', 'hỗ trợ', 'xử lý'],
        'when_to_see_doctor': ['khi nào', 'cần khám', 'đi bác sĩ', 'cơ sở y tế']
    }

    @staticmethod
    def detect_intent(query: str) -> List[str]:
        """Phát hiện intent từ query (có thể có nhiều intent)"""
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
        """Lấy keywords để boost sections dựa trên intent"""
        keywords = []
        for intent in intents:
            if intent in QueryIntent.SECTION_BOOST:
                keywords.extend(QueryIntent.SECTION_BOOST[intent])
        return list(set(keywords))  # Remove duplicates


# ============================================
# DISEASE-SPECIFIC KEYWORD BOOSTING (TĂNG TRỌNG SỐ THEO BỆNH ĐÍCH)
# ============================================

# Lớp này giải quyết triệt để lỗi "Râu ông nọ cắm cằm bà kia".
# Nếu người dùng đã gõ đích danh tên một bệnh (vd: Sốt xuất huyết),
# hệ thống phải ép thuật toán tìm kiếm ưu tiên lấy tài liệu của đúng bệnh đó.
class DiseaseDetector:
    """Detect specific diseases in query for targeted retrieval"""

    # Cấu trúc từ điển (Dictionary) ánh xạ từ khóa bệnh lý sang tên file văn bản.
    # [QUAN TRỌNG VỀ THUẬT TOÁN]: Các cụm từ dài/cụ thể (như 'viêm họng kích ứng')
    # BẮT BUỘC phải khai báo trước các cụm từ ngắn ('viêm họng') để tránh lỗi Nuốt từ (Shadowing)
    # trong quá trình duyệt vòng lặp.
    DISEASE_TO_FILE = {
        # Cụm dài/cụ thể trước
        'viêm họng kích ứng': 'viem_hong_kich_ung.txt',
        'viêm họng cấp': 'viem_hong_cap.txt',
        'đau họng': 'viem_hong_cap.txt',
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

        # Cụm ngắn sau (tránh match sớm)
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

        # Nhóm từ khóa kết hợp (Symptom combination keywords)
        # Cho phép detect dựa trên combo triệu chứng đặc trưng của bệnh
        'chóng mặt': 'sot_xuat_huyet.txt',
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
        """Detect disease keywords in query and return target filenames"""
        query_lower = query.lower()
        target_files = []

        # Sắp xếp từ khóa theo độ dài giảm dần bằng hàm lambda.
        # Đảm bảo các cụm từ đa âm tiết luôn được ưu tiên bắt khớp trước cụm đơn âm tiết.
        sorted_keywords = sorted(
            DiseaseDetector.DISEASE_TO_FILE.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )

        # Mảng lưu vết để xử lý hiện tượng chồng lấp (Overlapping Spans)
        matched_spans = []

        for disease_keyword, filename in sorted_keywords:
            idx = query_lower.find(disease_keyword)
            if idx == -1:
                continue

            span = (idx, idx + len(disease_keyword))
            overlaps = any(
                not (span[1] <= s[0] or span[0] >= s[1])
                for s in matched_spans
            )
            if overlaps:
                continue

            matched_spans.append(span)
            if filename not in target_files:
                target_files.append(filename)

        return target_files


# Import modules
sys.path.append(str(Path(__file__).parent.parent.parent))


# Lớp RAGRetriever đóng vai trò "Bộ máy Tìm kiếm cốt lõi".
# Chuyển đổi mô hình từ Truy xuất Đơn lớp (Chỉ dùng FAISS) sang Truy xuất Lai (Hybrid Retrieval),
# kết hợp cả Dense Search (Vector) và Sparse Search (Keyword/Từ khóa BM25).
class RAGRetriever:
    """
    Hybrid Retriever: Dense (FAISS) + Sparse (BM25) + RRF

    Sử dụng Reciprocal Rank Fusion để kết hợp điểm từ:
    - Dense Retrieval: FAISS vector search (semantic similarity - Khớp ý nghĩa)
    - Sparse Retrieval: BM25 keyword matching (lexical similarity - Khớp chính xác từ vựng)
    """

    def __init__(
        self,
        vector_store: VectorStore = None,
        embedder: EmbeddingModel = None,
        top_k: int = None
    ):
        """Khởi tạo Hybrid Retriever"""
        self.top_k = top_k or config.TOP_K_RETRIEVAL

        # Khởi tạo mô hình học sâu sinh Vector
        if embedder:
            self.embedder = embedder
        else:
            if config.DEBUG:
                logger.debug("Dang khoi tao Embedding Model...")
            self.embedder = EmbeddingModel(use_vietnamese=True)

        # Khởi tạo Cơ sở dữ liệu Vector (FAISS)
        if vector_store:
            self.vector_store = vector_store
        else:
            if config.DEBUG:
                logger.debug("Dang khoi tao Vector Store...")
            self.vector_store = VectorStore(
                dimension=self.embedder.embedding_dim)
            self.load_vector_store()

        # ============================================
        # BM25 SPARSE RETRIEVAL (CƠ CHẾ TÌM KIẾM THƯA BẰNG TỪ KHÓA)
        # ============================================
        # Corpus: danh sách toàn bộ văn bản (đã tokenized) để huấn luyện mô hình BM25.
        self.bm25_corpus = []
        self.bm25_model = None
        self._build_bm25_index()

        if config.DEBUG:
            logger.info(f"Hybrid Retriever san sang! (Top-K: {self.top_k})")
            logger.info(
                f"  Dense: FAISS ({self.vector_store.index.ntotal} docs)")
            logger.info(f"  Sparse: BM25 ({len(self.bm25_corpus)} docs)")

    def _tokenize_text(self, text: str) -> List[str]:
        """Tokenize text cho BM25 (simple whitespace splitting)"""
        # Tách từ cơ bản dựa trên khoảng trắng.
        # Đối với tiếng Việt, nếu sau này muốn tối ưu BM25 tốt hơn nữa,
        # có thể thay thế bằng Underthesea tại bước này.
        return text.lower().split()

    def _build_bm25_index(self):
        """
        Build BM25 index từ documents trong vector store
        Đảm bảo cả Dense và Sparse đang quét trên cùng một nguồn dữ liệu (Corpus).
        """
        if not hasattr(self.vector_store, 'documents') or not self.vector_store.documents:
            logger.warning(
                "Vector store chua co documents, bo qua BM25 indexing")
            self.bm25_corpus = []
            self.bm25_model = None
            return

        logger.info("Dang build BM25 index...")

        self.bm25_corpus = [
            self._tokenize_text(doc.get('content', ''))
            for doc in self.vector_store.documents
        ]

        # Khởi tạo mô hình BM25Okapi với tập dữ liệu.
        self.bm25_model = BM25Okapi(self.bm25_corpus)

        logger.info(
            f"BM25 index da san sang: {len(self.bm25_corpus)} documents")

    def _extract_disease_keywords(self, query: str) -> List[str]:
        """Backward-compatible disease keyword extraction for legacy tests/callers."""
        if not query:
            return []

        query_lower = query.lower()
        matched_keywords = []
        matched_spans = []

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
        """Load vector store từ file"""
        load_path = path or str(
            config.VECTOR_STORE_DIR / "health_faiss.index")
        success = self.vector_store.load(load_path)

        if success:
            if config.DEBUG:
                logger.debug(
                    f"Da load vector store: {self.vector_store.index.ntotal} documents")
        else:
            if config.DEBUG:
                logger.debug(
                    "Chua co vector store. Hay build truoc bang build_rag_pipeline.py")

        return success

    # Hàm truy xuất cốt lõi. Áp dụng quy trình phức hợp 6 bước (Pipeline)
    # để đảm bảo tài liệu đầu ra luôn chuẩn xác nhất có thể.
    def retrieve(self, query: str, top_k: int = None, apply_threshold: bool = True) -> List[Dict]:
        """
        HYBRID RETRIEVAL với RRF (Reciprocal Rank Fusion) + SMART SECTION BOOSTING

        Pipeline:
        1. Query Intent Detection -> Nhận diện ý định câu hỏi.
        2. Dense Retrieval (FAISS) -> Tìm kiếm theo ngữ nghĩa vector.
        3. Sparse Retrieval (BM25) -> Tìm kiếm theo từ khóa thô.
        4. Section Boosting -> Phạt/Thưởng điểm các tài liệu khớp ý định.
        5. RRF Fusion -> Dung hợp thứ hạng từ 2 hệ thống tìm kiếm.
        6. Re-rank -> Sắp xếp lại và lọc tính đa dạng (Diversity Filter).
        """
        k = top_k or self.top_k

        # Bước 1: NHẬN DIỆN Ý ĐỊNH
        detected_intents = QueryIntent.detect_intent(query)
        section_keywords = QueryIntent.get_section_keywords(detected_intents)

        if config.DEBUG:
            logger.debug(f"\n Detected Intents: {detected_intents}")
            logger.debug(f" Section Keywords: {section_keywords}")

        # Bước 1.5: PHÁT HIỆN TÊN BỆNH CỤ THỂ ĐỂ TARGET
        target_diseases = DiseaseDetector.detect_diseases(query)

        if config.DEBUG and target_diseases:
            logger.debug(f" Target Diseases Detected: {target_diseases}")

        # Bước 2: CHUẨN HÓA VÀ MỞ RỘNG TRUY VẤN (QUERY EXPANSION)
        normalized_query = normalize_query(query)
        query_for_search = normalized_query if normalized_query else query

        # Nếu người dùng hỏi dạng "X là dấu hiệu của bệnh gì?",
        # hệ thống tự động bóc tách phần râu ria, chỉ giữ lại "triệu chứng X"
        # để nạp vào hệ thống tìm kiếm, giúp tăng độ mở (Recall).
        if 'disease_from_symptom' in detected_intents:
            symptom_part = re.sub(
                r'\s*(là|có thể là|có phải là)?\s*(dấu hiệu|triệu chứng|biểu hiện)?\s*'
                r'(của)?\s*(bệnh gì|bệnh nào|những bệnh gì)[?.]?\s*$',
                '', query_for_search, flags=re.IGNORECASE).strip()
            if symptom_part and symptom_part != query_for_search:
                query_for_search = symptom_part
                if config.DEBUG:
                    logger.debug(
                        f" Query expanded (symptom only): '{query_for_search}'")

        if config.DEBUG:
            logger.debug(f"\n Original Query: '{query}'")
            if normalized_query != query.lower().strip():
                logger.debug(f" Normalized Query: '{query_for_search}'")

        # ============================================
        # TÌM KIẾM DENSE (FAISS VECTOR SEARCH)
        # ============================================
        query_embedding = self.embedder.encode_text(query_for_search)

        # Lấy dải truy xuất ban đầu (Initial Retrieval) rộng hơn Top-K
        # để đảm bảo không lọt mất tài liệu tốt.
        candidate_size = config.TOP_K_INITIAL if hasattr(
            config, 'TOP_K_INITIAL') else max(k * 2, 12)

        if config.DEBUG:
            logger.debug(f" Stage 1: Retrieving {candidate_size} candidates")

        dense_results = self.vector_store.search(
            query_embedding, top_k=candidate_size)

        # Trích xuất và lưu thứ hạng (Rank) của FAISS vào biến dense_ranks.
        dense_ranks = {}
        for rank, doc in enumerate(dense_results, start=1):
            doc_id = id(doc)
            dense_ranks[doc_id] = rank
            doc['_doc_id'] = doc_id

        if config.DEBUG:
            logger.debug(
                f" Dense (FAISS): Retrieved {len(dense_results)} candidates")

        # ============================================
        # TÌM KIẾM SPARSE (BM25 KEYWORD MATCHING)
        # ============================================
        sparse_ranks = {}
        _bm25_doc_map = {}

        if self.bm25_model and self.bm25_corpus:
            query_tokens = self._tokenize_text(query_for_search)
            bm25_scores = self.bm25_model.get_scores(query_tokens)

            # Sắp xếp điểm số BM25 theo thứ tự giảm dần
            scored_docs = [(score, idx)
                           for idx, score in enumerate(bm25_scores)]
            scored_docs.sort(reverse=True, key=lambda x: x[0])

            _bm25_doc_map = {}
            for rank, (score, doc_idx) in enumerate(scored_docs[:candidate_size], start=1):
                if doc_idx < len(self.vector_store.documents):
                    doc = self.vector_store.documents[doc_idx]
                    doc_id = id(doc)
                    sparse_ranks[doc_id] = rank
                    _bm25_doc_map[doc_id] = doc

            if config.DEBUG:
                logger.debug(
                    f" Sparse (BM25): Scored {len(sparse_ranks)} documents")
        else:
            if config.DEBUG:
                logger.warning(
                    " BM25 chua khoi tao, chi dung Dense retrieval")

        # ============================================
        # DUNG HỢP RECIPROCAL RANK FUSION (RRF) VÀ TĂNG TRỌNG SỐ
        # ============================================
        # Hằng số làm mượt (Smoothing constant), thường = 60
        rrf_k = config.RRF_K
        rrf_scores = {}

        all_doc_ids = set(dense_ranks.keys()) | set(sparse_ranks.keys())

        _dense_doc_map = {
            doc.get('_doc_id'): doc for doc in dense_results if doc.get('_doc_id')}
        _all_doc_map = {**_dense_doc_map, **_bm25_doc_map}

        for doc_id in all_doc_ids:
            # Nếu tài liệu chỉ xuất hiện ở một thuật toán, thuật toán kia sẽ cho rank = vô cực (1e9)
            dense_rank = dense_ranks.get(doc_id, 1e9)
            sparse_rank = sparse_ranks.get(doc_id, 1e9)

            # Công thức cốt lõi của thuật toán RRF: Điểm số = 1/(k + Rank_Dense) + 1/(k + Rank_Sparse)
            rrf_score = (1.0 / (rrf_k + dense_rank)) + \
                (1.0 / (rrf_k + sparse_rank))

            doc = _all_doc_map.get(doc_id)

            # [THUẬT TOÁN ĐIỀU CHỈNH ĐIỂM SỐ]: Tăng trọng số cho mục tương ứng với Ý định (Intent)
            if section_keywords and doc:
                content = doc.get('content', '').lower()
                metadata = doc.get('metadata', {})
                section_title = metadata.get('section_title', '').lower()
                boost_factor = 1.0
                for keyword in section_keywords:
                    # Tăng 15% điểm nếu cụm từ ý định xuất hiện trong Tiêu đề hoặc Đầu đoạn văn.
                    if keyword.lower() in section_title or keyword.lower() in content[:200]:
                        boost_factor += 0.15
                if boost_factor > 1.0:
                    rrf_score *= boost_factor
                    if config.DEBUG:
                        logger.debug(
                            f" Section boost: {boost_factor:.2f}x for {metadata.get('source', 'Unknown')}")

            # [THUẬT TOÁN ĐIỀU CHỈNH ĐIỂM SỐ]: Tăng mạnh (2x) cho tài liệu khớp đích danh tên bệnh.
            if target_diseases and doc:
                source = doc.get('metadata', {}).get('source', '')
                if source in target_diseases:
                    # Đảm bảo các tài liệu về bệnh này leo lên đầu mảng.
                    disease_boost = 1.3
                    rrf_score *= disease_boost
                    if config.DEBUG:
                        logger.debug(
                            f" Disease boost: {disease_boost:.2f}x for {source}")

            rrf_scores[doc_id] = rrf_score

        # ============================================
        # SẮP XẾP LẠI (RE-RANK) VÀ ĐÓNG GÓI KẾT QUẢ
        # ============================================
        final_results = []
        _added_doc_ids = set()

        for doc in dense_results:
            doc_id = doc.get('_doc_id')
            if doc_id in rrf_scores:
                doc_copy = doc.copy()
                doc_copy['rrf_score'] = rrf_scores[doc_id]
                doc_copy.pop('_doc_id', None)
                doc_copy['dense_score'] = doc.get('score', 999)
                final_results.append(doc_copy)
                _added_doc_ids.add(doc_id)

        # Trường hợp Đặc biệt: Bổ sung các tài liệu CHỈ có trong BM25 (BM25-only)
        # Giúp cứu lại các văn bản bị FAISS bỏ sót nhưng chứa chính xác từ khóa người dùng gõ.
        for doc_id, doc in _bm25_doc_map.items():
            if doc_id not in _added_doc_ids and doc_id in rrf_scores:
                doc_copy = doc.copy()
                doc_copy['rrf_score'] = rrf_scores[doc_id]
                doc_copy.pop('_doc_id', None)
                # Gán điểm Dense giả = 0.0 để lách qua bộ lọc L2 Threshold (vốn chỉ xét khoảng cách Dense)
                doc_copy['dense_score'] = 0.0
                doc_copy['_bm25_only'] = True
                final_results.append(doc_copy)
                if config.DEBUG:
                    src = doc.get('metadata', {}).get('source', 'Unknown')
                    logger.debug(
                        f" BM25-only doc added: {src} (RRF: {rrf_scores[doc_id]:.6f})")

        # Sắp xếp mảng kết quả cuối cùng theo điểm RRF (giảm dần)
        final_results.sort(key=lambda x: x.get('rrf_score', 0), reverse=True)

        if config.DEBUG:
            logger.debug("\n Stage 2: RRF ranked candidates")
            for i, doc in enumerate(final_results[:10], 1):
                rrf = doc.get('rrf_score', 0)
                dense = doc.get('dense_score', 999)
                source = doc.get('metadata', {}).get('source', 'Unknown')
                logger.debug(
                    f"  [{i}] RRF: {rrf:.6f} | Dense: {dense:.4f} | {source}")

        # ============================================
        # BỘ LỌC NGƯỠNG VÀ TÍNH ĐA DẠNG (THRESHOLD & DIVERSITY FILTERING)
        # ============================================
        if apply_threshold:
            threshold = config.RELEVANCE_THRESHOLD

            # Cắt bỏ các tài liệu có khoảng cách L2 (dense_score) cao hơn ngưỡng cho phép.
            filtered = [doc for doc in final_results
                        if doc.get('_bm25_only') or doc.get('dense_score', 999) <= threshold]

            if config.DEBUG:
                logger.debug(
                    f"\n Stage 3: L2 Threshold Filtering ({threshold})")
                logger.debug(f" Kept: {len(filtered)} docs")
                logger.debug(
                    f" Removed: {len(final_results) - len(filtered)} docs")

            if not filtered:
                logger.warning(" No documents passed relevance threshold")
                return []

            # Kích hoạt bộ lọc đa dạng nguồn (Diversity Filter).
            # Ngăn chặn trường hợp Top 3 tài liệu trả về đều trích xuất từ CÙNG 1 file,
            # đảm bảo người dùng có được bức tranh tổng thể đa chiều.
            final_output = self._apply_diversity_filter(filtered, k)

            if config.DEBUG:
                logger.debug(
                    f"\n FINAL OUTPUT: Top-{k} documents after diversity filtering")
                for i, doc in enumerate(final_output, 1):
                    rrf = doc.get('rrf_score', 0)
                    dense = doc.get('dense_score', 999)
                    metadata = doc.get('metadata', {})
                    source = metadata.get('source', 'Unknown')
                    section = metadata.get('section_title', 'N/A')
                    logger.debug(
                        f"  [{i}] RRF: {rrf:.6f} | Dense: {dense:.4f} | {source} | {section}")

            # KIỂM SOÁT ĐÍCH DANH BỆNH (SINGLE DISEASE FOCUS)
            # Nếu người dùng hỏi đúng 1 bệnh duy nhất, loại bỏ hoàn toàn các tài liệu
            # của các bệnh khác ra khỏi danh sách kết quả, đảm bảo tính trong sạch của Context.
            if target_diseases and len(target_diseases) == 1:
                target = target_diseases[0]

                focused_docs = [
                    doc for doc in final_output
                    if doc.get('metadata', {}).get('source') == target
                ]

                if len(focused_docs) >= 1:
                    if config.DEBUG:
                        logger.debug(
                            f" Single-disease focus applied: {target}")
                    final_output = focused_docs[:k]

            return final_output

        return final_results[:k]

    def _apply_diversity_filter(self, docs: List[Dict], max_results: int) -> List[Dict]:
        """Apply diversity filter to prioritize DIFFERENT SOURCES (diseases) over same source"""
        if len(docs) <= max_results:
            return docs

        source_docs = {}
        for doc in docs:
            source = doc.get('metadata', {}).get('source', 'Unknown')
            if source not in source_docs:
                source_docs[source] = []
            source_docs[source].append(doc)

        selected = []

        # CHIẾN LƯỢC 1 (Ưu tiên bề rộng): Lấy 1 Chunk từ TỪNG bệnh khác nhau.
        # Đảm bảo câu hỏi bắt bệnh như "sốt và đau đầu" sẽ truy xuất đủ Cúm mùa, Sốt xuất huyết...
        sources_used = set()
        for doc in docs:
            if len(selected) >= max_results:
                break
            source = doc.get('metadata', {}).get('source', 'Unknown')
            if source not in sources_used:
                selected.append(doc)
                sources_used.add(source)
                if config.DEBUG:
                    logger.debug(f"  Added first chunk from: {source}")

        # CHIẾN LƯỢC 2 (Khai thác chiều sâu): Nếu còn dư slot Top-K, nạp tiếp Chunk thứ 2
        # của các bệnh đã chọn, NHƯNG phải chắc chắn Chunk đó thuộc về Section khác
        # (Ví dụ: Không được nạp 2 đoạn của mục "Triệu chứng").
        if len(selected) < max_results:
            source_sections = {s: set() for s in sources_used}
            for doc in selected:
                source = doc.get('metadata', {}).get('source', 'Unknown')
                section = doc.get('metadata', {}).get('section_title', '')
                source_sections[source].add(section)

            for source in sources_used:
                if len(selected) >= max_results:
                    break
                remaining_docs = [
                    d for d in source_docs[source] if d not in selected]
                for doc in remaining_docs:
                    if len(selected) >= max_results:
                        break
                    section = doc.get('metadata', {}).get('section_title', '')
                    if section not in source_sections[source]:
                        selected.append(doc)
                        source_sections[source].add(section)
                        if config.DEBUG:
                            logger.debug(
                                f"  Added 2nd chunk from: {source} (section: {section})")
                        break

        # CHIẾN LƯỢC 3 (Dự phòng): Nếu qua 2 bước lọc trên mà vẫn chưa đủ số lượng Max Results,
        # lấp đầy bằng các Chunk có điểm số cao nhất còn lại.
        if len(selected) < max_results:
            remaining = [d for d in docs if d not in selected]
            selected.extend(remaining[:max_results - len(selected)])

        if config.DEBUG:
            sources_count = {}
            for doc in selected:
                source = doc.get('metadata', {}).get('source', 'Unknown')
                sources_count[source] = sources_count.get(source, 0) + 1
            logger.debug(
                f" Diversity filter result: {len(sources_count)} unique sources")
            for source, count in sources_count.items():
                logger.debug(f"  - {source}: {count} chunk(s)")

        return selected

    def retrieve_with_threshold(
        self,
        query: str,
        similarity_threshold: float = 0.5,
        top_k: int = None
    ) -> List[Dict]:
        """Retrieve documents với ngưỡng similarity tối thiểu"""
        results = self.retrieve(query, top_k)

        # Lọc kết quả dựa trên điểm RRF
        filtered = [
            doc for doc in results
            if doc.get('rrf_score', 0) >= similarity_threshold
        ]

        return filtered

    def retrieve_and_format(self, query: str, top_k: int = None) -> str:
        """Retrieve và format thành context string chuẩn bị cấp cho LLM"""
        results = self.retrieve(query, top_k)

        if not results:
            return "Không tìm thấy thông tin liên quan."

        context_parts = []

        for i, doc in enumerate(results, 1):
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            source = metadata.get('source', 'Unknown')
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
