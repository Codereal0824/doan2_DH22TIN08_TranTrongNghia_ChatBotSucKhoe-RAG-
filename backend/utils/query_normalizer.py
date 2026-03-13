"""
Query Normalizer - Chuẩn hóa câu hỏi người dùng trước khi tìm kiếm
"""
import re
from typing import Dict, List

# ============================================
# NORMALIZATION RULES
# ============================================

# Từ dư thừa cần loại bỏ
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

# Chuẩn hóa cách diễn đạt đồng nghĩa
SYNONYM_PATTERNS = {
    # Triệu chứng
    r'\bbị ho (nhẹ|nhiều|khan)\b': 'ho',
    r'\bbị ho\b': 'ho',
    r'\bho (nhẹ|nhiều|khan)\b': 'ho',
    r'\bbị sốt\b': 'sốt',
    r'\bsốt (nhẹ|cao)\b': 'sốt',
    r'\bbị (đau đầu|nhức đầu)\b': 'đau đầu',
    r'\bđau (đầu|họng|bụng)\b': 'đau \\1',
    r'\bviêm (họng|phổi|amidan)\b': 'viêm \\1',

    # Hành động
    r'\b(làm gì khi|làm sao khi|xử lý khi)\b': 'cách chăm sóc',
    r'\b(phòng tránh|ngăn ngừa|tránh)\b': 'phòng ngừa',
    r'\b(điều trị|chữa trị|khắc phục)\b': 'cách chăm sóc',
    r'\bcách (xử lý|giải quyết|đối phó)\b': 'cách chăm sóc',
    r'\bnên làm gì\b': 'cách chăm sóc',

    # Nguyên nhân
    r'\b(tại sao|vì sao|do đâu)\b': 'nguyên nhân',
    r'\blý do\b': 'nguyên nhân',

    # Triệu chứng/dấu hiệu (map về "dấu hiệu" vì tài liệu dùng "Dấu hiệu thường gặp")
    r'\b(biểu hiện|triệu chứng)\b': 'dấu hiệu',

    # NEW: Query expansion cho câu hỏi ngắn về dấu hiệu
    r'\b(các )?dấu hiệu (của|là gì)\b': 'dấu hiệu thường gặp',
    r'\b(các )?triệu chứng (của|là gì)\b': 'dấu hiệu thường gặp',

    # Khi nào đến bác sĩ
    r'\b(khi nào nên đi (khám|bác sĩ|bệnh viện))\b': 'khi nào đến cơ sở y tế',
    r'\bđến bác sĩ\b': 'đến cơ sở y tế',

    # MỞ RỘNG TRIỆU CHỨNG - Chuẩn hóa về dạng ngắn nhất khớp với tài liệu
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

    # DISEASE SYNONYMS - Map tên gọi khác về tên chính
    r'\btiểu đường\b': 'đái tháo đường',
    r'\btieu duong\b': 'dai thao duong',
    r'\bbéo phì\b': 'béo phì lối sống',
    r'\btrào ngược\b': 'rối loạn tiêu hóa',
    r'\bđau dạ dày\b': 'rối loạn tiêu hóa',
}

# Các từ khóa chăm sóc sức khỏe quan trọng (GIỮ LẠI)
HEALTH_KEYWORDS = [
    'ho', 'sốt', 'đau đầu', 'cảm lạnh', 'viêm họng', 'cúm',
    'stress', 'mất ngủ', 'mệt mỏi', 'chóng mặt',
    'triệu chứng', 'nguyên nhân', 'phòng ngừa', 'chăm sóc',
    'dinh dưỡng', 'vận động', 'nghỉ ngơi',
]

# Patterns để phát hiện câu hỏi chẩn đoán bệnh (cần từ chối)
MEDICAL_DIAGNOSIS_PATTERNS = [
    r'\btôi (có |đang )?(bị|mắc)\b',
    r'\bcon tôi (có |đang )?(bị|mắc)\b',
    r'\b(chẩn đoán|kết luận|chắc là) bệnh\b',
    r'\b(thuốc|đơn thuốc) điều trị\b',
    r'\b(u não|ung thư|hiểm nghèo)\b.*tôi\b'
]


# ============================================
# QUERY NORMALIZATION FUNCTION
# ============================================

def normalize_query(query: str) -> str:
    """
    Chuẩn hóa câu hỏi người dùng trước khi tìm kiếm

    Args:
        query: Câu hỏi gốc từ người dùng

    Returns:
        str: Câu hỏi đã chuẩn hóa
    """
    if not query or not query.strip():
        return query

    # Chuyển về lowercase
    normalized = query.lower().strip()

    # Log original query
    print(f"\n🔄 QUERY NORMALIZATION:")
    print(f"   Original: '{query}'")

    # 1. Áp dụng synonym patterns (đồng nghĩa)
    for pattern, replacement in SYNONYM_PATTERNS.items():
        if re.search(pattern, normalized):
            old_normalized = normalized
            normalized = re.sub(pattern, replacement, normalized)
            if old_normalized != normalized:
                print(f"   ✏️  Synonym: '{pattern}' → '{replacement}'")

    # 2. Loại bỏ filler words (từ dư thừa)
    for filler in FILLER_WORDS:
        if re.search(filler, normalized):
            old_normalized = normalized
            normalized = re.sub(filler, '', normalized)
            if old_normalized != normalized:
                print(f"   ❌ Removed: '{filler}'")

    # 3. Loại bỏ dấu câu thừa
    normalized = re.sub(r'[?!.,;]+', ' ', normalized)

    # 4. Loại bỏ khoảng trắng thừa
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    # Log final normalized query
    print(f"   Normalized: '{normalized}'")

    return normalized


def extract_health_intent(query: str) -> Dict[str, any]:
    """
    Phân tích ý định câu hỏi về sức khỏe

    Args:
        query: Câu hỏi (đã hoặc chưa chuẩn hóa)

    Returns:
        Dict với intent analysis
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

    # Kiểm tra health keywords
    if any(keyword in query_lower for keyword in HEALTH_KEYWORDS):
        intent['is_health_query'] = True

    # Phân loại intent
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

    # NGUY HIỂM: Yêu cầu điều trị/thuốc
    if re.search(r'(điều trị|chữa trị|dùng thuốc|uống thuốc|liều|kê đơn)', query_lower):
        intent['mentions_treatment'] = True

    if re.search(r'(paracetamol|ibuprofen|aspirin|kháng sinh|thuốc)', query_lower):
        intent['mentions_medicine'] = True

    return intent


def should_block_query(query: str) -> tuple[bool, str]:
    """
    Kiểm tra xem có nên chặn câu hỏi không (yêu cầu y khoa lâm sàng)

    Args:
        query: Câu hỏi người dùng

    Returns:
        (should_block: bool, reason: str)
    """
    intent = extract_health_intent(query)

    # Chặn nếu hỏi về điều trị hoặc thuốc
    if intent['mentions_treatment']:
        return True, "Yêu cầu thông tin điều trị (ngoài phạm vi)"

    if intent['mentions_medicine']:
        return True, "Yêu cầu thông tin về thuốc (ngoài phạm vi)"

    return False, ""


# ============================================
# TESTING
# ============================================

def test_normalizer():
    """Test query normalization"""
    test_cases = [
        "Bị ho nhẹ thì làm gì?",
        "Triệu chứng cảm lạnh là gì?",
        "Làm sao để phòng tránh sốt?",
        "Khi nào nên đi khám bác sĩ khi bị ho?",
        "Cách chữa trị đau đầu như thế nào?",
        "Tại sao lại bị stress?",
        "Tôi nên uống thuốc gì khi sốt?",  # Should block
        "Liều lượng paracetamol là bao nhiêu?",  # Should block
    ]

    print("=" * 70)
    print("QUERY NORMALIZATION TEST")
    print("=" * 70)

    for query in test_cases:
        print(f"\n{'─' * 70}")
        normalized = normalize_query(query)

        # Check if should block
        should_block, reason = should_block_query(query)
        if should_block:
            print(f"   🚫 BLOCKED: {reason}")

        # Extract intent
        intent = extract_health_intent(query)
        print(
            f"   Intent: {[k for k, v in intent.items() if v and k != 'is_health_query']}")


if __name__ == "__main__":
    test_normalizer()
