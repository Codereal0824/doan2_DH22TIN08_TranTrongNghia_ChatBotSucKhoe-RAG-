"""
Prompts - Quản lý System Prompts và Templates cho Chatbot
"""

# ============================================
# PROMPTS - UPDATED FOR CORRECT RAG BEHAVIOR
# (Version dùng cho Đồ án 2 – đã loại bỏ over-blocking)
# ============================================

# ==========================================================
# 1. CHỈ CẤM HÀNH VI CHẨN ĐOÁN / KÊ ĐƠN (KHÔNG CẤM GIÁO DỤC)
# ==========================================================

FORBIDDEN_TERMS = [
    "kê đơn",
    "toa thuốc",
    "y lệnh"
]

FORBIDDEN_MEDICAL_ADVICE_PATTERNS = [
    "tôi chẩn đoán",
    "tôi kết luận",
    "bạn đang mắc",
    "bạn bị bệnh"
]

FORBIDDEN_PHRASES = []  # bỏ kiểm duyệt suy diễn để tránh block oan

# ==========================================================
# 2. FALLBACK RESPONSE (GIỮ NGUYÊN)
# ==========================================================

STRICT_FALLBACK_RESPONSE = """Hiện tài liệu chưa cung cấp thông tin về nội dung này.
Bạn nên tham khảo nhân viên y tế để được tư vấn."""

NO_DOCS_FOUND_RESPONSE = STRICT_FALLBACK_RESPONSE

# ==========================================================
# 3. SYSTEM PROMPT — RAG VỚI KHẢ NĂNG SUY LUẬN LOGIC
# ==========================================================

HEALTH_CHATBOT_SYSTEM_PROMPT = """Bạn là Chatbot Giáo dục Sức khỏe hoạt động dựa trên hệ thống RAG (Retrieval-Augmented Generation).
Bạn KHÔNG phải bác sĩ. Mọi câu trả lời phải dựa HOÀN TOÀN và DUY NHẤT vào nội dung trong <context>.

⛔ QUY TẮC TUYỆT ĐỐI — KHÔNG ĐƯỢC VI PHẠM:

1. NGÔN NGỮ CHUẨN MỰC
- Sử dụng 100% Tiếng Việt. 
- TUYỆT ĐỐI KHÔNG sử dụng bất kỳ ký tự tiếng Trung (Hán tự), Pinyin, hay tiếng nước ngoài nào (ngoại trừ tên bệnh quốc tế như COVID-19).

2. GROUNDING & LOGIC (CHỐNG RÂU ÔNG NỌ CẮM CẰM BÀ KIA)
- Chỉ đề cập bệnh, triệu chứng, thông tin có XUẤT HIỆN CHÍNH XÁC trong <context>.
- NGUYÊN TẮC LIÊN KẾT: Nếu người dùng hỏi Thực phẩm X có chữa/giúp Bệnh Y không, nhưng <context> chỉ nói Thực phẩm X dùng cho Bệnh Z -> BẮT BUỘC trả lời KHÔNG hoặc dùng FALLBACK. Tuyệt đối không bê công dụng của Bệnh Z sang trả lời cho Bệnh Y.

3. ĐỘ DÀI (GIỚI HẠN CỨNG)
- TỐI ĐA 3 câu. Dừng lại sau câu thứ 3.
- Kết thúc bằng: Nguồn: [tên file từ <available_sources>]

4. CÂU HỎI TRIỆU CHỨNG
- "X là dấu hiệu của bệnh gì?" → MỘT CÂU DUY NHẤT: liệt kê TẤT CẢ bệnh trong <context> có triệu chứng đó. KHÔNG liệt kê các chủ đề như Tiêm chủng, Vận động.
- "Tôi bị X và Y" → HAI CÂU. Câu 1: X và Y có thể là dấu hiệu của Bệnh A, Bệnh B... Câu 2: Lời khuyên chăm sóc. KHÔNG chẩn đoán.
- "Triệu chứng X có phải của bệnh Y không?" → Câu 1 bắt đầu bằng CÓ hoặc KHÔNG.

5. CÂU HỎI KHẲNG ĐỊNH ("X có giúp/chữa/phòng Z không?")
- Câu 1: BẮT ĐẦU BẰNG "CÓ" HOẶC "KHÔNG".
- Nếu <context> KHÔNG đề cập TRỰC TIẾP mối quan hệ X↔Z → dùng FALLBACK ngay.

6. FALLBACK (QUY TẮC TỪ CHỐI)
"Hiện tài liệu chưa cung cấp thông tin về nội dung này. Bạn nên tham khảo nhân viên y tế để được tư vấn."
Nguồn: Không có"""

# ==========================================================
# 4. RAG PROMPT TEMPLATE - ENHANCED FOR ALL REQUIREMENTS
# ==========================================================

RAG_PROMPT_TEMPLATE = """<user_query>
{question}
</user_query>

<context>
{context}
</context>

<available_sources>
{sources}
</available_sources>

<instructions>
BƯỚC 1: KIỂM TRA LIÊN QUAN — dùng FALLBACK khi:
- <context> không chứa thông tin liên quan trực tiếp đến câu hỏi.
- Câu hỏi hỏi về một thực phẩm/thành phần cụ thể (sầu riêng, vitamin C, mật ong, gừng...) mà không có tài liệu nào trực tiếp nói về nó.
- Câu hỏi "X có chữa/trị/phòng bệnh không?" mà <context> không đề cập rõ mối quan hệ đó.
KHÔNG ghép thông tin gián tiếp từ các tài liệu khác để trả lời câu hỏi trực tiếp. Nếu không có câu trả lời rõ ràng → FALLBACK.
FALLBACK: ĐÚNG NGUYÊN VĂN:
"Hiện tài liệu chưa cung cấp thông tin về nội dung này. Bạn nên tham khảo nhân viên y tế để được tư vấn."
Nguồn: Không có
(KHÔNG giải thích, KHÔNG liệt kê bệnh không liên quan)

BƯỚC 2: NẾU CONTEXT CÓ LIÊN QUAN
QUY TẮC TRẢ LỜI (theo thứ tự bắt buộc):
1. Câu 1: TRẢ LỜI THẲNG câu hỏi — không dẫn dắt, không giới thiệu.
2. Câu 2–3 (nếu cần): thông tin bổ sung từ <context>.
3. TỐI ĐA 3 câu. Dừng lại sau câu thứ 3.

QUY TẮC NỘI DUNG:
- Chỉ dùng thông tin từ <context>. KHÔNG thêm kiến thức ngoài.
- Nếu hỏi "triệu chứng X là bệnh gì?" hoặc "X là dấu hiệu của bệnh gì?" → Câu 1 (và CHỈ câu 1): liệt kê TẤT CẢ bệnh có triệu chứng đó trong <context>, viết dạng "X là dấu hiệu của: BệnhA, BệnhB, BệnhC.". DỪNG. KHÔNG viết thêm câu nào mô tả triệu chứng của từng bệnh.
- Nếu hỏi "triệu chứng X có phải của bệnh Y không?" → Câu 1: xác nhận CÓ/KHÔNG với bệnh Y. Câu 2: nêu bệnh khác trong <context> cũng có triệu chứng đó.
- Câu hỏi "X có Y không?" / "X có chữa được Z không?" → Câu 1: trả lời CÓ hoặc KHÔNG dựa trên <context>. KHÔNG nói "không có thông tin cụ thể". Nếu context không nói rõ → dùng FALLBACK.
- Nếu hỏi so sánh → nêu 1 điểm giống, 1 điểm khác rõ nhất.
- KHÔNG nói "tài liệu không đủ", "thông tin không được mô tả rõ", "không có thông tin cụ thể về việc", hoặc bất kỳ nhận xét nào về tài liệu.
- TUYỆT ĐỐI KHÔNG đề cập bệnh/tình trạng không có trong <context>.
- HỎI VỀ TRIỆU CHỨNG CỦA 1 BỆNH CỤ THỂ (VD: "Triệu chứng của cảm lạnh là gì?"): Bạn CHỈ ĐƯỢC PHÉP đọc và lấy thông tin từ tài liệu của chính bệnh đó. BỎ QUA HOÀN TOÀN thông tin từ các tài liệu bệnh khác có trong <context>. Bắt đầu bằng: "Triệu chứng của [Tên bệnh] bao gồm: [liệt kê]". DỪNG LẠI SAU KHI LIỆT KÊ XONG. TUYỆT ĐỐI KHÔNG mở rộng thêm và TUYỆT ĐỐI KHÔNG nhắc đến tên bất kỳ bệnh nào khác.
- CÂU HỎI CHUNG: Nếu người dùng hỏi kiến thức sức khỏe phổ quát (VD: Chế độ ăn lành mạnh là gì?, Tập thể dục ra sao?), TUYỆT ĐỐI KHÔNG lấy các quy tắc kiêng khem khắc nghiệt của một bệnh cụ thể (VD: kiêng hải sản của bệnh Gout, kiêng đường của bệnh Tiểu đường) để làm lời khuyên chung cho mọi người. Nếu trong tài liệu chỉ có thông tin kiêng khem của bệnh, hãy ghi rõ: "Đối với người bệnh [Tên bệnh], chế độ ăn cần...".
</instructions>

<output_format>
CÂU TRẢ LỜI (tối đa 3 câu):
[Câu 1: trả lời trực tiếp]
[Câu 2–3: thông tin bổ sung nếu cần]

Nguồn: [CHỈ liệt kê file mà bạn THỰC SỰ trích dẫn thông tin trong câu trả lời trên. Nếu câu trả lời chỉ dùng 1 file → chỉ liệt kê 1 file. Tối đa 3 file.]
</output_format>"""

# ==========================================================
# 5. SEMANTIC RELEVANCE CHECK (NEW - FIX HALLUCINATION)
# ==========================================================


def check_context_relevance(question: str, context: str) -> bool:
    """
    Kiểm tra xem context có thực sự liên quan đến câu hỏi không.

    Mục đích: Ngăn chặn hallucination khi câu hỏi ngoài dataset.

    Args:
        question: Câu hỏi của user
        context: Context đã retrieve

    Returns:
        bool: True nếu context có liên quan, False nếu không liên quan
    """
    import re

    # Nếu context trống hoặc quá ngắn
    if not context or len(context.strip()) < 20:
        return False

    # Vietnamese stopwords — lưu ý: KHÔNG đưa động từ quan trọng ('chữa', 'trị') vào đây
    # vì sẽ làm mất khả năng nhận biết câu hỏi điều trị
    stopwords = {
        'là', 'của', 'và', 'có', 'thì', 'được', 'trong', 'cho', 'với', 'theo',
        'để', 'từ', 'hoặc', 'như', 'nếu', 'khi', 'hay', 'những', 'các', 'về',
        'bị', 'mà', 'vì', 'rằng', 'này', 'đó', 'nào', 'gì', 'không', 'sẽ',
        'thế', 'tại', 'sao', 'ăn', 'uống', 'bệnh', 'triệu', 'chứng',
        # Đại từ nhân xưng — không xuất hiện trong tài liệu y tế, làm tăng mẫu số sai
        'tôi', 'tao', 'mình', 'anh', 'chị', 'bạn', 'ông', 'bà', 'em',
        # Từ bổ nghĩa mức độ — không có trong context tài liệu
        'nhẹ', 'nặng', 'nhiều', 'ngày',
    }

    # Tokenize câu hỏi và lấy các từ quan trọng
    try:
        from underthesea import word_tokenize
        question_tokens = word_tokenize(question.lower())
    except Exception:
        # Fallback nếu underthesea chưa cài hoặc lỗi
        question_tokens = question.lower().split()

    # Lọc bỏ stopwords và từ quá ngắn
    key_terms = [
        token for token in question_tokens
        if len(token) > 2 and token not in stopwords
    ]

    # Nếu không có key term nào (câu hỏi quá chung chung)
    if not key_terms:
        return True  # Cho phép LLM xử lý

    # Chuẩn hóa context (lowercase, bỏ dấu ngoặc)
    context_normalized = context.lower()
    context_normalized = re.sub(
        r'\[tài liệu \d+ - [^\]]+\]', '', context_normalized)

    # Đếm số key terms xuất hiện trong context
    matched_terms = 0
    for term in key_terms:
        if term in context_normalized:
            matched_terms += 1
        elif ' ' in term:
            # Compound token từ underthesea (vd: "sốt nhẹ", "mệt mỏi")
            # Kiểm tra từng từ con — đủ 1 từ con có nghĩa (len > 2) xuất hiện là khớp
            if any(w in context_normalized for w in term.split() if len(w) > 2):
                matched_terms += 1

    # Nếu ít hơn tỉ lệ key terms xuất hiện → context không liên quan
    relevance_ratio = matched_terms / len(key_terms)

    # Threshold: 0.15 — Mức chuẩn nhất để không chặn nhầm câu hỏi có nhiều từ thừa
    if relevance_ratio < 0.15:
        return False

    return True


# ==========================================================
# 6. FORMAT CONTEXT (GIỮ NGUYÊN)
# ==========================================================

# Mapping filename → tên bệnh tiếng Việt để inject vào context header
# Giúp LLM biết chunk này thuộc bệnh/chủ đề nào dù chunk ở giữa file
_FILENAME_TO_DISEASE = {
    'cam_lanh.txt': 'Cảm lạnh',
    'cum_mua.txt': 'Cúm mùa',
    'sot_xuat_huyet.txt': 'Sốt xuất huyết',
    'Covid19.txt': 'COVID-19',
    'dai_thao_duong.txt': 'Đái tháo đường',
    'tang_huyet_ap.txt': 'Tăng huyết áp',
    'benh_tim_mach.txt': 'Bệnh tim mạch',
    'Gout.txt': 'Bệnh gút (Gout)',
    'thoai_hoa_khop_goi.txt': 'Thoái hóa khớp gối',
    'hen_phe_quan.txt': 'Hen phế quản',
    'viem_gan_B.txt': 'Viêm gan B',
    'viem_hong_cap.txt': 'Viêm họng cấp',
    'viem_hong_kich_ung.txt': 'Viêm họng kích ứng',
    'viem_mui_di_ung.txt': 'Viêm mũi dị ứng',
    'viem_xoang.txt': 'Viêm xoang',
    'viem_da_co_dia.txt': 'Viêm da cơ địa',
    'viem_ket_mac.txt': 'Viêm kết mạc (đau mắt đỏ)',
    'Kho_mat.txt': 'Khô mắt',
    'ho_thong_thuong.txt': 'Ho thông thường',
    'mat_ngu.txt': 'Mất ngủ',
    'mat_nuoc.txt': 'Mất nước',
    'say_nang.txt': 'Say nắng',
    'stress.txt': 'Căng thẳng (Stress)',
    'tram_cam.txt': 'Trầm cảm',
    'roi_loan_lo_au.txt': 'Rối loạn lo âu',
    'suc_khoe_tam_than.txt': 'Sức khỏe tâm thần',
    'roi_loan_tieu_hoa.txt': 'Rối loạn tiêu hóa',
    'tao_bon_chuc_nang.txt': 'Táo bón',
    'dau_bung_kinh.txt': 'Đau bụng kinh',
    'hoi_chung_u_nan_buong_trung.txt': 'Hội chứng buồng trứng đa nang',
    'beo_phi_do_loi_song.txt': 'Béo phì do lối sống',
    'luoi_van_dong.txt': 'Lười vận động',
    'suy_dinh_duong.txt': 'Suy dinh dưỡng',
    'coi_xuong.txt': 'Còi xương',
    'suy_giap.txt': 'Suy giáp',
    'soi_than.txt': 'Sỏi thận',
    'nhiem_trung_duong_tiet_nieu.txt': 'Nhiễm trùng đường tiết niệu',
    'mun_trung_ca.txt': 'Mụn trứng cá',
    'Dau_lung.txt': 'Đau lưng',
    'ung_thu.txt': 'Ung thư',
    'tiem_chung.txt': 'Tiêm chủng',
}


def format_context(retrieved_docs: list) -> str:
    """
    Format retrieved documents thành context string.
    Inject tên bệnh vào header để LLM biết chunk thuộc bệnh/chủ đề nào.

    Args:
        retrieved_docs: List of dicts với 'content' và 'metadata'

    Returns:
        str: Formatted context
    """
    if not retrieved_docs:
        return "Không có thông tin liên quan."

    context_parts = []

    for i, doc in enumerate(retrieved_docs, 1):
        content = doc.get('content', '')
        metadata = doc.get('metadata', {})
        source = metadata.get('source', 'Unknown')

        # Thêm tên bệnh vào header để LLM không cần phán đoán từ filename
        disease_name = _FILENAME_TO_DISEASE.get(source, '')
        if disease_name:
            header = f"[Tài liệu {i} - {source} | Bệnh/Chủ đề: {disease_name}]"
        else:
            header = f"[Tài liệu {i} - {source}]"

        context_parts.append(f"{header}\n{content}")

    return "\n---\n".join(context_parts)

# ==========================================================
# 6. SAFETY FILTER — CHỈ CHẶN CHẨN ĐOÁN THẬT SỰ
# ==========================================================


def violates_policy(answer: str) -> bool:
    """
    Kiểm tra xem câu trả lời có vi phạm chính sách không

    Args:
        answer: Câu trả lời cần kiểm tra

    Returns:
        bool: True nếu vi phạm
    """
    if not answer:
        return False

    text_lower = answer.lower()

    # Red flags for diagnosis
    diagnosis_flags = [
        "tôi chẩn đoán",
        "bạn bị bệnh",
        "tôi kết luận"
    ]

    # Check diagnosis flags
    if any(flag in text_lower for flag in diagnosis_flags):
        return True

    return False


def sanitize_answer(answer: str) -> str:
    """
    Làm sạch câu trả lời và áp dụng safety filter

    Args:
        answer: Câu trả lời gốc từ LLM

    Returns:
        str: Câu trả lời an toàn hoặc fallback
    """
    if not answer or not answer.strip():
        return STRICT_FALLBACK_RESPONSE

    if violates_policy(answer):
        return STRICT_FALLBACK_RESPONSE

    return answer

# ==========================================================
# 8. VERIFICATION AI - POST-GENERATION VALIDATION
# ==========================================================


def extract_disease_names(text: str) -> list:
    """
    Trích xuất tên bệnh từ text (context hoặc answer)
    """
    import re

    # Common disease patterns in Vietnamese
    disease_patterns = [
        r'(?:bệnh )?(cảm lạnh|cúm|cúm mùa)',
        r'(?:bệnh )?(?:viêm )?họng(?:\s+cấp)?(?:\s+kích ứng)?',
        r'(?:bệnh )?(?:viêm )?mũi(?:\s+dị ứng)?',
        r'(?:bệnh )?(?:viêm )?xoang',
        r'sốt(?:\s+xuất huyết)?',
        r'đái tháo đường|tiểu đường',
        r'cao huyết áp|tăng huyết áp',
        r'gout|bệnh gút',
        r'béo phì',
        r'stress|căng thẳng',
        r'mất ngủ|khó ngủ',
        r'táo bón',
        r'rối loạn tiêu hóa',
        r'suy dinh dưỡng',
        r'ho(?:\s+thông thường)?',
        r'mất nước|thiếu nước',
    ]

    diseases = []
    text_lower = text.lower()

    for pattern in disease_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            disease = match.group(0)
            if disease not in diseases:
                diseases.append(disease)

    return diseases


def extract_sources_from_answer(answer: str) -> list:
    """
    Trích xuất sources từ phần cuối câu trả lời
    """
    import re

    source_match = re.search(r'Nguồn:\s*(.+?)(?:\n|$)', answer, re.IGNORECASE)
    if not source_match:
        return []

    source_text = source_match.group(1).strip()

    if 'không có' in source_text.lower():
        return []

    sources = re.findall(r'[\w_.-]+\.txt', source_text)
    sources = [s for s in sources if len(s) > 4 and not s.startswith('.')]
    return sources


def extract_sources_from_context(context: str) -> list:
    """
    Trích xuất danh sách file từ context (format: [Tài liệu 1 - filename.txt])
    """
    import re

    matches = re.findall(
        r'\[Tài liệu \d+ - ([\w_.-]+\.txt)(?:\s*\|[^\]]*)?\]', context)
    seen = set()
    ordered = []
    for s in matches:
        if s not in seen:
            seen.add(s)
            ordered.append(s)
    return ordered


def verify_answer(question: str, context: str, draft_answer: str) -> str:
    """
    Xác minh và sửa lỗi câu trả lời trước khi trả về user.
    """
    import re

    _FALLBACK_MARKERS_V = [
        "hiện tài liệu chưa cung cấp",
        "không có thông tin về nội dung này",
        "nguồn: không có",
    ]

    if not draft_answer or any(m in draft_answer.lower() for m in _FALLBACK_MARKERS_V):
        return STRICT_FALLBACK_RESPONSE

    if not context or context.strip() == "Không có thông tin liên quan.":
        return f"{STRICT_FALLBACK_RESPONSE}\n\nNguồn: Không có"

    context_lower = context.lower()
    answer_lower = draft_answer.lower()

    # RULE 1: HALLUCINATION DETECTION
    DATASET_DISEASE_TERMS = [
        'ebola', 'malaria', 'sốt rét', 'viêm màng não',
        'viêm não nhật bản', 'parkinson', 'alzheimer',
        'multiple sclerosis', 'xơ cứng bì', 'lupus', 'bệnh crohn',
        'lao phổi', 'bệnh lao', 'bạch hầu', 'uốn ván', 'bại liệt',
        'covid-19', 'covid19', 'covid 19', 'coronavirus', 'sars-cov', 'sars',
        'sốt xuất huyết', 'dengue',
        'đái tháo đường', 'tiểu đường type',
        'tăng huyết áp', 'cao huyết áp',
        'hen phế quản', 'hen suyễn',
        'bệnh gút', 'gout',
        'mụn trứng cá',
        'viêm gan b',
        'viêm da cơ địa',
        'sỏi thận',
        'nhiễm trùng đường tiết niệu',
        'rối loạn lo âu',
        'trầm cảm',
        'ung thư',
        'u nang buồng trứng',
        'suy giáp',
        'viêm kết mạc', 'đau mắt đỏ',
        'thoái hóa khớp',
        'còi xương',
        'say nắng',
        'suy dinh dưỡng',
        'béo phì',
        'rối loạn tiêu hóa',
        'viêm họng cấp', 'viêm họng kích ứng',
        'cảm lạnh',
        'cúm mùa',
        'mất nước',
        'mất ngủ',
        'stress',
        'suy tim', 'nhồi máu cơ tim', 'rối loạn nhịp tim',
        'đau lưng',
        'đau bụng kinh',
        'sỏi tiết niệu',
    ]

    for term in DATASET_DISEASE_TERMS:
        if term in answer_lower and term not in context_lower:
            print(
                f"🚨 HALLUCINATION DETECTED: '{term}' not in retrieved context")
            return f"{STRICT_FALLBACK_RESPONSE}\n\nNguồn: Không có"

    # RULE 2: NO MEDICAL DIAGNOSIS
    diagnosis_phrases = [
        'bạn bị bệnh', 'bạn mắc bệnh', 'bạn đang bị',
        'tôi chẩn đoán', 'tôi kết luận'
    ]
    if any(phrase in answer_lower for phrase in diagnosis_phrases):
        draft_answer = re.sub(
            r'bạn (bị|mắc|đang bị) ([\w\s]+?)(?=[,.\n]|$)',
            r'các triệu chứng này có thể liên quan đến \2',
            draft_answer,
            flags=re.IGNORECASE
        )

    # RULE 3: REMOVE DATASET COMMENTARY
    commentary_patterns = [
        r'thông tin không được đề cập rõ ràng trong tài liệu',
        r'tài liệu (không|chưa) (cung cấp|mô tả|nói đến|nhắc đến|ghi rõ|đề cập)( đầy đủ| chi tiết| rõ ràng)?',
        r'thông tin (không|chưa) (được|đề cập)( chi tiết| đầy đủ| rõ ràng)?',
        r'dataset (không|chưa) có( đủ)? thông tin',
        r'theo tài liệu hiện có[,]?',
        r'trong phạm vi tài liệu[,]?',
        r'thông tin (trong|từ) (tài liệu|dataset) (không|chưa|hạn chế)',
        r'không có tài liệu nào (mô tả|nói đến|đề cập)',
        r'ngoài phạm vi của tài liệu',
        r'các tài liệu (không|chưa) (cung cấp|đề cập)',
        r'[Tt]uy nhiên[,\s]+không có thông tin[^.!?]*[.!?]\s*',
        r'không có thông tin cụ thể về(?: việc)?[^.!?]*[.!?]\s*',
        r'không có thông tin(?: cụ thể)? về(?: việc)?[^.!?\n]*[.!?]\s*',
        r'chưa có thông tin(?: cụ thể)?[^.!?\n]*[.!?]\s*',
        r'[Tt]uy nhiên[,\s]+chưa có thông tin[^.!?]*[.!?]\s*',
        r'[^.!?\n]*không được đề cập trực tiếp[^.!?]*[.!?]\s*',
        r'[^.!?\n]*trong các tài liệu cung cấp[^.!?]*[.!?]\s*',
        r'[Tt]uy nhiên[,\s]+[^.!?]*được khuyến nghị[^.!?]*[.!?]\s*',
        r'[Tt]uy nhiên[,\s]+[^.!?]*được khuyến khích[^.!?]*[.!?]\s*',
        r'[Vv]í dụ[,\s]+trong chăm sóc cho[^.!?]*[.!?]\s*',
        r'trong chăm sóc[^.!?]*được khuyến[^.!?]*[.!?]\s*',
    ]
    for pattern in commentary_patterns:
        draft_answer = re.sub(pattern, '', draft_answer, flags=re.IGNORECASE)

    # RULE 4: SOURCE VALIDATION
    sources_in_context = extract_sources_from_context(context)
    sources_in_answer = extract_sources_from_answer(draft_answer)

    if sources_in_answer:
        invalid_sources = [
            s for s in sources_in_answer if s not in sources_in_context]
        if invalid_sources:
            print(
                f"⚠️ INVALID SOURCES in answer: {invalid_sources}. Replacing with context sources.")
            valid_sources = [
                s for s in sources_in_answer if s in sources_in_context]
            replacement = ', '.join(
                valid_sources) if valid_sources else ', '.join(sources_in_context)
            draft_answer = re.sub(
                r'Nguồn:.*?(?:\n|$)',
                f'Nguồn: {replacement}\n',
                draft_answer,
                flags=re.IGNORECASE
            )

  # RULE 5: LENGTH ENFORCEMENT
    lines = draft_answer.split('\n')
    main_lines, source_line = [], ""
    for line in lines:
        if line.strip().lower().startswith('ngu\u1ed3n:'):
            source_line = line.strip()
        elif line.strip():
            main_lines.append(line)

    main_text = ' '.join(main_lines).strip()

    if not main_text:
        return f"{STRICT_FALLBACK_RESPONSE}\n\nNguồn: Không có"

    sentences = re.split(r'(?<=[.!?])\s+', main_text)

    # =====================================================
    # ✅ FIX: MÁY CHÉM PYTHON CHO CÂU HỎI "LÀ BỆNH GÌ"
    # =====================================================
    is_pure_question = bool(re.search(
        r'là (dấu hiệu|triệu chứng|biểu hiện) của bệnh gì|là bệnh gì', question.lower()))

    # Nếu là câu hỏi bắt bệnh -> Chặt đứt giữ đúng 1 câu đầu tiên
    if is_pure_question and len(sentences) > 1:
        main_text = sentences[0].strip()
        if not main_text.endswith(('.', '!', '?')):
            main_text += '.'

    # Các câu hỏi khác -> Ép tối đa 3 câu
    elif len(sentences) > 3:
        main_text = ' '.join(sentences[:3]).strip()
        if not main_text.endswith(('.', '!', '?')):
            main_text += '.'

    final = main_text.strip()
    if source_line:
        final += f"\n\n{source_line}"

    return final.strip()

# ==========================================================
# 7. GREETING / FAREWELL (GIỮ NGUYÊN)
# ==========================================================


GREETING_RESPONSES = [
    "Xin chào! Tôi có thể hỗ trợ bạn tìm hiểu thông tin sức khỏe.",
]

FAREWELL_RESPONSES = [
    "Chúc bạn luôn khỏe mạnh!",
]

# ==========================================================
# HELPER FUNCTIONS (GIỮ NGUYÊN)
# ==========================================================


def format_sources(retrieved_docs: list) -> str:
    """Format danh sách nguồn tham khảo"""
    if not retrieved_docs:
        return ""

    sources = []
    seen = set()

    for doc in retrieved_docs:
        metadata = doc.get('metadata', {})
        source = metadata.get('source', 'Unknown')

        if source not in seen:
            sources.append(source)
            seen.add(source)

    return ", ".join(sources)


def is_greeting(text: str) -> bool:
    """Kiểm tra xem có phải lời chào không - dùng word boundary"""
    import re
    greetings = [
        r'\bxin chào\b', r'\bchào\b', r'\bhello\b',
        r'\bhi\b', r'\bhey\b', r'\bchào bạn\b', r'\bchào bot\b'
    ]
    text_lower = text.lower().strip()
    for pattern in greetings:
        if re.search(pattern, text_lower):
            return True
    return False


def is_farewell(text: str) -> bool:
    """Kiểm tra xem có phải lời tạm biệt không"""
    farewells = ['tạm biệt', 'bye', 'goodbye',
                 'hẹn gặp lại', 'cảm ơn', 'thank']
    text_lower = text.lower().strip()
    return any(farewell in text_lower for farewell in farewells)


def build_messages(
    question: str,
    context: str,
    system_prompt: str = None,
    chat_history: list = None,
    sources: str = ""
) -> list:
    """Xây dựng messages cho Groq API"""
    messages = []

    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt
        })
    else:
        messages.append({
            "role": "system",
            "content": HEALTH_CHATBOT_SYSTEM_PROMPT
        })

    if chat_history:
        for user_msg, bot_msg in chat_history[-5:]:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": bot_msg})

    user_message = RAG_PROMPT_TEMPLATE.format(
        context=context,
        question=question,
        sources=sources if sources else "Không có tài liệu nào được truy xuất"
    )
    messages.append({
        "role": "user",
        "content": user_message
    })

    return messages


DISCLAIMER_TEXT = """
⚠️ LƯU Ý QUAN TRỌNG:
Chatbot này chỉ cung cấp thông tin sức khỏe tham khảo, KHÔNG thay thế cho tư vấn y tế chuyên nghiệp.
Mọi quyết định về sức khỏe cần được thực hiện dưới sự hướng dẫn của bác sĩ hoặc chuyên gia y tế có chứng chỉ hành nghề.
"""

# ==========================================================
# EXPORT
# ==========================================================

__all__ = [
    'HEALTH_CHATBOT_SYSTEM_PROMPT',
    'RAG_PROMPT_TEMPLATE',
    'sanitize_answer',
    'format_context',
    'format_sources',
    'GREETING_RESPONSES',
    'FAREWELL_RESPONSES',
    'STRICT_FALLBACK_RESPONSE',
    'NO_DOCS_FOUND_RESPONSE',
    'DISCLAIMER_TEXT',
    'violates_policy',
    'is_greeting',
    'is_farewell',
    'build_messages',
    'FORBIDDEN_TERMS',
    'FORBIDDEN_MEDICAL_ADVICE_PATTERNS',
    'FORBIDDEN_PHRASES'
]
