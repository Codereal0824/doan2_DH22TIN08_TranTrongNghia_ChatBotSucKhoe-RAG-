"""
Query Normalizer - Chuẩn hóa câu hỏi người dùng trước khi tìm kiếm
"""
import re
from typing import Dict

# ============================================
# NORMALIZATION RULES (QUY TẮC CHUẨN HÓA VĂN BẢN)
# ============================================

# Danh sách từ dừng (Stopwords/Filler Words) đặc thù cho dạng câu hỏi giao tiếp.
# Loại bỏ các từ này giúp hệ thống tìm kiếm thưa (Sparse Retrieval - BM25)
# không bị nhiễu bởi các từ có tần suất xuất hiện cao nhưng mang ít ngữ nghĩa.
FILLER_WORDS = [
    r'\bnhư nào\b',
    r'\bnhư thế nào\b',
    r'\bra sao\b',
    r'\bthế nào\b',
    r'\bgiúp tôi\b',
    r'\bgiúp mình\b',
    r'\bcho tôi\b',
    r'\bcho mình\b',
    r'\bhãy\b',
    r'\bvui lòng\b',
    r'\bxin\b',
]

# Cấu trúc từ điển (Dictionary Mapping) quy định các Mẫu Đồng nghĩa (Synonym Patterns).
# Kỹ thuật này giải quyết vấn đề Khác biệt Từ vựng (Vocabulary Mismatch) giữa
# văn phong nói của người dùng và văn phong học thuật trong tài liệu y khoa.
SYNONYM_PATTERNS = {
    # Nhóm Triệu chứng: Ép chuẩn về danh từ gốc
    r'\bbị ho (nhẹ|nhiều|khan)\b': 'ho',
    r'\bbị ho\b': 'ho',
    r'\bho (nhẹ|nhiều|khan)\b': 'ho',
    r'\bbị sốt\b': 'sốt',
    r'\bsốt (nhẹ|cao)\b': 'sốt',
    r'\bbị (đau đầu|nhức đầu)\b': 'đau đầu',
    # Sử dụng Backreference (\1) để giữ lại hậu tố
    r'\bđau (đầu|họng|bụng)\b': 'đau \\1',
    r'\bviêm (họng|phổi|amidan)\b': 'viêm \\1',

    # Nhóm Hành động/Cách xử trí
    r'\b(làm gì khi|làm sao khi|xử lý khi)\b': 'cách chăm sóc',
    r'\b(phòng tránh|ngăn ngừa|tránh)\b': 'phòng ngừa',
    r'\b(điều trị|chữa trị|khắc phục)\b': 'cách chăm sóc',
    r'\bcách (xử lý|giải quyết|đối phó)\b': 'cách chăm sóc',
    r'\bnên làm gì\b': 'cách chăm sóc',

    # Nhóm Nguyên nhân
    r'\b(tại sao|vì sao|do đâu)\b': 'nguyên nhân',
    r'\blý do\b': 'nguyên nhân',

    # Nhóm Nhận biết: Đồng bộ hóa với cấu trúc tiêu đề "Dấu hiệu thường gặp" trong Dataset
    r'\b(biểu hiện|triệu chứng)\b': 'dấu hiệu',
    r'\b(các )?dấu hiệu (của|là gì)\b': 'dấu hiệu thường gặp',
    r'\b(các )?triệu chứng (của|là gì)\b': 'dấu hiệu thường gặp',

    # Nhóm Cảnh báo y tế
    r'\b(khi nào nên đi (khám|bác sĩ|bệnh viện))\b': 'khi nào đến cơ sở y tế',
    r'\bđến bác sĩ\b': 'đến cơ sở y tế',

    # Nhóm MỞ RỘNG TRIỆU CHỨNG (Symptom Expansion) - Chuẩn hóa về dạng ngắn nhất khớp với tài liệu
    r'\bbị (mệt mỏi|mệt|kiệt sức|uể oải)\b': 'mệt mỏi',
    r'\b(mệt|kiệt sức|uể oải)\b': 'mệt mỏi',
    r'\bsốt (kéo dài|liên tục|cao|nhẹ|vừa)\b': 'sốt',
    r'\bbị (buồn nôn|nôn mửa|nôn ói|ói)\b': 'buồn nôn',
    r'\b(nôn mửa|nôn ói|ói)\b': 'buồn nôn',
    r'\bbị (chóng mặt|choáng váng|hoa mắt)\b': 'chóng mặt',
    r'\b(choáng váng|hoa mắt)\b': 'chóng mặt',
    r'\bbị (khó thở|thở khó|thở dốc|thở gấp)\b': 'khó thở',
    r'\b(thở khó|thở dốc|thở gấp)\b': 'khó thở',
    r'\bbị (tiêu chảy|đi tháo|ỉa chảy|đi ngoài nhiều)\b': 'tiêu chảy',
    r'\b(đi tháo|ỉa chảy)\b': 'tiêu chảy',
    r'\bbị (phát ban|nổi ban|nổi mề đay|nổi mày đay|ngứa da)\b': 'phát ban',
    r'\b(nổi ban|nổi mề đay|nổi mày đay)\b': 'phát ban',
    r'\bngạt mũi\b': 'nghẹt mũi',
    r'\bbị (nghẹt mũi|ngạt mũi|tắc mũi)\b': 'nghẹt mũi',
    r'\bbị (đau họng|rát họng|ngứa họng|đau cổ họng)\b': 'đau họng',
    r'\b(rát họng|ngứa họng|đau cổ họng)\b': 'đau họng',
    r'\bbị (đau lưng|đau lưng dưới|nhức lưng)\b': 'đau lưng',
    r'\b(nhức lưng|đau lưng dưới)\b': 'đau lưng',
    r'\bbị (đau khớp|nhức khớp|đau xương khớp)\b': 'đau khớp',
    r'\b(nhức khớp|đau xương khớp)\b': 'đau khớp',
    r'\bviêm (xoang|mũi|tai|da co địa|da)\b': r'viêm \1',
    r'\bbị (căng thẳng|lo lắng nhiều|lo âu)\b': 'stress',
    r'\b(căng thẳng|lo lắng)\b': 'stress',

    # Nhóm Ánh xạ Bệnh lý (Disease Synonyms)
    r'\btiểu đường\b': 'đái tháo đường',
    r'\btieu duong\b': 'dai thao duong',
    r'\bbéo phì\b': 'béo phì lối sống',
    r'\btrào ngược\b': 'rối loạn tiêu hóa',
    r'\bđau dạ dày\b': 'rối loạn tiêu hóa',
}

# Bộ Tự điển Thuật ngữ Cốt lõi (Core Terminology Lexicon).
# Dùng để kích hoạt phân luồng (Routing) đối với các câu hỏi về sức khỏe.
HEALTH_KEYWORDS = [
    'ho', 'sốt', 'đau đầu', 'cảm lạnh', 'viêm họng', 'cúm',
    'stress', 'mất ngủ', 'mệt mỏi', 'chóng mặt',
    'triệu chứng', 'nguyên nhân', 'phòng ngừa', 'chăm sóc',
    'dinh dưỡng', 'vận động', 'nghỉ ngơi',
]

# Các Mẫu cấm kỵ (Forbidden Patterns) liên quan đến Chẩn đoán Lâm sàng.
# Dùng cho Tầng bảo vệ (Safety Gate) đầu tiên trước khi gọi LLM.
MEDICAL_DIAGNOSIS_PATTERNS = [
    r'\btôi (có |đang )?(bị|mắc)\b',
    r'\bcon tôi (có |đang )?(bị|mắc)\b',
    r'\b(chẩn đoán|kết luận|chắc là) bệnh\b',
    r'\b(thuốc|đơn thuốc) điều trị\b',
    r'\b(u hiểu|ung thư|hiểm nghèo)\b.*tôi\b'
]


# ============================================
# QUERY NORMALIZATION FUNCTION (HÀM XỬ LÝ CHÍNH)
# ============================================

def normalize_query(query: str) -> str:
    """
    Chuẩn hóa câu hỏi người dùng trước khi tìm kiếm

    Args:
        query: Câu hỏi gốc từ người dùng

    Returns:
        str: Câu hỏi đã chuẩn hóa (Stemmed/Lemmatized equivalent)
    """
    if not query or not query.strip():
        return query

    # Bước 1: Lowercasing (Chuyển chữ thường) để đảm bảo Case-Insensitive matching
    normalized = query.lower().strip()

    # Log quá trình biến đổi để hỗ trợ Debugging
    print("\n[THONG TIN] QUERY NORMALIZATION:")
    print(f"   Original: '{query}'")

    # Bước 2: Kích hoạt bộ lọc Đồng nghĩa (Synonym mapping)
    for pattern, replacement in SYNONYM_PATTERNS.items():
        if re.search(pattern, normalized):
            old_normalized = normalized
            normalized = re.sub(pattern, replacement, normalized)
            if old_normalized != normalized:
                print(f"   [CHI TIET] Synonym: '{pattern}' -> '{replacement}'")

    # Bước 3: Cắt tỉa Từ dư thừa (Stopword Removal)
    for filler in FILLER_WORDS:
        if re.search(filler, normalized):
            old_normalized = normalized
            normalized = re.sub(filler, '', normalized)
            if old_normalized != normalized:
                print(f"   [XOA BO] Removed: '{filler}'")

    # Bước 4: Dọn dẹp Dấu câu (Punctuation Removal)
    normalized = re.sub(r'[?!.,;]+', ' ', normalized)

    # Bước 5: Cắt xén khoảng trắng thừa (Whitespace normalization)
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    print(f"   Normalized: '{normalized}'")

    return normalized

# Hàm Heuristic dựa trên Quy tắc (Rule-based Intent Extraction).
# Phân rã câu hỏi thành một vector đặc trưng Boolean (Boolean Feature Vector)
# để luồng RAG biết cách định tuyến và cấu hình trọng số truy xuất phù hợp.


def extract_health_intent(query: str) -> Dict[str, any]:
    """
    Phân tích ý định câu hỏi về sức khỏe

    Args:
        query: Câu hỏi (đã hoặc chưa chuẩn hóa)

    Returns:
        Dict với intent analysis (Feature Vector)
    """
    query_lower = query.lower()

    intent = {
        'is_health_query': False,
        'asks_for_symptoms': False,
        'asks_for_causes': False,
        'asks_for_care': False,
        'asks_for_prevention': False,
        'asks_for_when_doctor': False,
        'mentions_treatment': False,
        'mentions_medicine': False,
    }

    # Kích hoạt cờ (Flag) nếu câu hỏi chứa từ khóa sức khỏe
    if any(keyword in query_lower for keyword in HEALTH_KEYWORDS):
        intent['is_health_query'] = True

    # Phân loại đa nhãn (Multi-label classification) bằng Regex
    if re.search(r'(triệu chứng|dấu hiệu|biểu hiện)', query_lower):
        intent['asks_for_symptoms'] = True

    if re.search(r'(nguyên nhân|tại sao|vì sao|do đâu)', query_lower):
        intent['asks_for_causes'] = True

    if re.search(r'(cách chăm sóc|làm gì|xử lý|chữa)', query_lower):
        intent['asks_for_care'] = True

    if re.search(r'(phòng (ngừa|tránh)|ngăn ngừa)', query_lower):
        intent['asks_for_prevention'] = True

    if re.search(r'(khi nào.*?(đến|đi|gặp|khám).*(bác sĩ|y tế|bệnh viện))', query_lower):
        intent['asks_for_when_doctor'] = True

    # KÍCH HOẠT CỜ ĐỎ (RED FLAGS): Phát hiện yêu cầu vi phạm đạo đức y tế
    if re.search(r'(điều trị|chữa trị|dùng thuốc|uống thuốc|liều|kê đơn)', query_lower):
        intent['mentions_treatment'] = True

    if re.search(r'(paracetamol|ibuprofen|aspirin|kháng sinh|thuốc)', query_lower):
        intent['mentions_medicine'] = True

    return intent

# Cổng An toàn Số 1 (Pre-Retrieval Safety Gate).
# Đóng vai trò như một tường lửa (Firewall) chặn đứng các yêu cầu độc hại
# trước khi chúng kịp đi vào hệ thống tìm kiếm Vector và tốn tài nguyên gọi LLM.


def should_block_query(query: str) -> tuple[bool, str]:
    """
    Kiểm tra xem có nên chặn câu hỏi không (yêu cầu y khoa lâm sàng)

    Args:
        query: Câu hỏi người dùng

    Returns:
        (should_block: bool, reason: str)
    """
    intent = extract_health_intent(query)

    # Từ chối phục vụ (Reject) nếu người dùng có ý định xin phác đồ điều trị
    if intent['mentions_treatment']:
        return True, "Yeu cau thong tin dieu tri (ngoai pham vi)"

    # Từ chối phục vụ nếu người dùng hỏi về Dược lý học chuyên sâu (Pharmacology)
    if intent['mentions_medicine']:
        return True, "Yeu cau thong tin ve thuoc (ngoai pham vi)"

    return False, ""
