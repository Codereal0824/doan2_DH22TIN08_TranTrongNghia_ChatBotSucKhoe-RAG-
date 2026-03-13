"""
Prompts - Quản lý System Prompts và Templates cho Chatbot
"""

# ============================================
# SYSTEM PROMPT - STRICT ANTI-HALLUCINATION MODE
# ============================================

HEALTH_CHATBOT_SYSTEM_PROMPT = """Bạn là hệ thống hỏi đáp sức khỏe sử dụng Retrieval-Augmented Generation (RAG).

NHIỆM VỤ DUY NHẤT:
Trả lời CHÍNH XÁC dựa trên nội dung có trong CONTEXT được cung cấp.

QUY TẮC BẮT BUỘC:

1. Chỉ sử dụng thông tin xuất hiện TRỰC TIẾP trong CONTEXT.
2. KHÔNG được:
   - Suy luận thêm.
   - Liên hệ kiến thức gần đúng.
   - Bổ sung thông tin "có liên quan".
   - Giải thích ngoài phạm vi tài liệu.
   - Dùng các cụm như: "Tuy nhiên", "Ngoài ra", "Liên quan", "Có thể".
3. Nếu CONTEXT không chứa thông tin trả lời câu hỏi:
   → Phải trả lời NGUYÊN VĂN: "Tôi không tìm thấy thông tin phù hợp trong dữ liệu hiện có."
4. Không được phép cung cấp bất kỳ thông tin bổ sung nào sau câu trả lời từ chối.
5. Không được cố gắng hữu ích ngoài dữ liệu (no helpful guessing).
6. Không sử dụng kiến thức đã được huấn luyện sẵn của mô hình.
7. KHÔNG chẩn đoán bệnh, KHÔNG kê đơn thuốc."""

3. NẾU KHÔNG CÓ THÔNG TIN PHẢN HỢP → NÓI NGẮN GỌN
   "Tôi không có thông tin về[chủ đề] trong cơ sở dữ liệu. Bạn nên tham khảo ý kiến bác sĩ để được tư vấn chi tiết.

   📚 Nguồn: Không có thông tin phù hợp"

3. NẾU KHÔNG CÓ THÔNG TIN PHẢN HỢP → NÓI NGẮN GỌN
   "Tôi không có thông tin về[chủ đề] trong cơ sở dữ liệu. Bạn nên tham khảo ý kiến bác sĩ để được tư vấn chi tiết.

   📚 Nguồn: Không có thông tin phù hợp"

4. NẾU NGƯỜI DÙNG HỎI VỀ CHẨN ĐOÁN → TRẢ LỜI:
   "Tôi không thể chẩn đoán bệnh. Các triệu chứng bạn mô tả có thể là dấu hiệu của [bệnh X theo ngữ cảnh]. Bạn nên đi khám bác sĩ để được thăm khám và chẩn đoán chính xác."

5. NẾU NGƯỜI DÙNG HỎI VỀ THUỐC/LIỀU LƯỢNG → TRẢ LỜI:
   "Tôi không thể tư vấn về thuốc và liều lượng. Hãy tham khảo bác sĩ hoặc dược sĩ để được hướng dẫn an toàn."

6. VỚI TRIỆU CHỨNG NGHIÊM TRỌNG → LUÔN KHUYẾN NGHỊ:
   "⚠️ Triệu chứng này có thể nghiêm trọng. Hãy đi khám bác sĩ ngay!"

7. PHÂN BIỆT RÕ RÀNG GIỮA CÁC BỆNH:
   - Tiểu đường: khát nước, đi tiểu nhiều, mệt mỏi, giảm cân
   - Đau dạ dày: đau thượng vị, đầy bụng, ợ hơi, buồn nôn
   - KHÔNG được nói triệu chứng của bệnh này là triệu chứng của bệnh kia

📋 ĐỊNH DẠNG TRẢ LỜI:

[Nội dung trả lời ngắn gọn, chính xác 100 % theo ngữ cảnh, 2-4 câu]

📚 Nguồn: [Tên nguồn cụ thể]

VÍ DỤ TRẢ LỜI TỐT:

User: "Tôi hay khát nước và đi tiểu nhiều, đây là bệnh gì?"
Context: [Có thông tin về triệu chứng tiểu đường]
Bot: "Khát nước liên tục và đi tiểu nhiều(đặc biệt ban đêm) là 2 trong 12 triệu chứng bất thường của bệnh tiểu đường. Đây là dấu hiệu cảnh báo quan trọng cần chú ý. Nếu bạn có các triệu chứng này kéo dài, hãy đi khám bác sĩ và xét nghiệm đường huyết để được chẩn đoán chính xác.

📚 Nguồn: 12_trieu_chung_bat_thuong_cua_benh_tieu_duong.txt"

VÍ DỤ TRẢ LỜI TỐT(không có thông tin):

User: "Thuốc metformin uống như thế nào?"
Bot: "Tôi không có đủ thông tin về cách dùng thuốc metformin trong cơ sở dữ liệu. Đây là thuốc kê đơn, bạn nên tham khảo bác sĩ hoặc dược sĩ để được hướng dẫn cách dùng, liều lượng và lưu ý an toàn phù hợp với tình trạng sức khỏe của bạn.

📚 Nguồn: Nguyên tắc an toàn dùng thuốc"

VÍ DỤ TRẢ LỜI TỐT(context không liên quan):

User: "Bệnh tiểu đường có triệu chứng gì?"
Context: [Chỉ có thông tin về viêm họng, cảm lạnh - KHÔNG có tiểu đường]
Bot: "Tôi không có thông tin về bệnh tiểu đường trong cơ sở dữ liệu. Bạn nên tham khảo ý kiến bác sĩ để được tư vấn chi tiết.

📚 Nguồn: Không có thông tin phù hợp"

❌ VÍ DỤ TRẢ LỜI SAI(KHÔNG được làm):

User: "Bệnh tiểu đường có triệu chứng gì?"
Context: [Chỉ có thông tin về viêm họng]
Bot SAI: "Tôi không có thông tin về tiểu đường. Viêm họng có triệu chứng đau họng, khó nuốt..."
→ SAI VÌ: Nói về viêm họng khi người dùng hỏi tiểu đường!

NHỚ: An toàn bệnh nhân là ưu tiên hàng đầu. Khi nghi ngờ → khuyên đi khám bác sĩ!"""


# ============================================
# RAG PROMPT TEMPLATE
# ============================================

RAG_PROMPT_TEMPLATE = """CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
Chỉ tóm tắt thông tin có thật trong CONTEXT, không thêm bất cứ điều gì khác."""


# ============================================
# CONTEXT FORMATTING
# ============================================

def format_context(retrieved_docs: list) -> str:
    """
    Format retrieved documents thành context string

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

        context_parts.append(
            f"[Tài liệu {i} - Nguồn: {source}]\n{content}\n"
        )

    return "\n---\n".join(context_parts)


def format_sources(retrieved_docs: list) -> str:
    """
    Format danh sách nguồn tham khảo

    Args:
        retrieved_docs: List of dicts

    Returns:
        str: Formatted sources
    """
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


# ============================================
# CONVERSATION TEMPLATES
# ============================================

GREETING_RESPONSES = [
    "Xin chào! Tôi là trợ lý tư vấn sức khỏe AI. Tôi có thể giúp gì cho bạn hôm nay?",
    "Chào bạn! Bạn cần tư vấn về vấn đề sức khỏe nào?",
    "Xin chào! Hãy cho tôi biết bạn muốn tìm hiểu về vấn đề sức khỏe gì nhé!"
]


FAREWELL_RESPONSES = [
    "Chúc bạn một ngày khỏe mạnh! Hãy chăm sóc sức khỏe tốt nhé! 🏥",
    "Tạm biệt! Nhớ đi khám định kỳ để bảo vệ sức khỏe! 👋",
    "Hẹn gặp lại! Giữ gìn sức khỏe nhé! 🌟"
]

# ============================================
# FALLBACK RESPONSE - When no docs found
# ============================================

NO_DOCS_FOUND_RESPONSE = """Tôi không tìm thấy thông tin liên quan trong cơ sở dữ liệu hiện có.

⚠️ LƯU Ý:
Hệ thống này chỉ cung cấp thông tin sức khỏe tham khảo từ các tài liệu đã được lưu trữ.
Để được tư vấn chính xác, bạn nên:
- Tham khảo ý kiến bác sĩ/chuyên gia y tế
- Đi khám tại cơ sở y tế uy tín
- Gọi đường dây tư vấn sức khỏe: 19003368

📚 Nguồn: Không tìm thấy tài liệu phù hợp"""


DISCLAIMER_TEXT = """
⚠️ LƯU Ý QUAN TRỌNG:
Chatbot này chỉ cung cấp thông tin sức khỏe tham khảo, KHÔNG thay thế cho tư vấn y tế chuyên nghiệp.
Mọi quyết định về sức khỏe cần được thực hiện dưới sự hướng dẫn của bác sĩ hoặc chuyên gia y tế có chứng chỉ hành nghề.
"""


# ============================================
# HELPER FUNCTIONS
# ============================================

def is_greeting(text: str) -> bool:
    """Kiểm tra xem có phải lời chào không - dùng word boundary"""
    import re

    # Danh sách lời chào với word boundary
    greetings = [
        r'\bxin chào\b',
        r'\bchào\b',
        r'\bhello\b',
        r'\bhi\b',  # Chỉ khớp "hi" là từ riêng, không phải "hiệu", "khi"
        r'\bhey\b',
        r'\bchào bạn\b',
        r'\bchào bot\b'
    ]

    text_lower = text.lower().strip()

    for pattern in greetings:
        if re.search(pattern, text_lower):
            return True


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
    chat_history: list = None
) -> list:
    """
    Xây dựng messages cho Groq API

    Args:
        question: Câu hỏi của user
        context: Context từ RAG
        system_prompt: System prompt
        chat_history: Lịch sử chat[[user_msg, bot_msg], ...]

    Returns:
        list: Messages cho API
    """
    messages = []

    # System prompt
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

    # Chat history
    if chat_history:
        for user_msg, bot_msg in chat_history[-5:]:  # Chỉ lấy 5 turn gần nhất
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": bot_msg})

    # Current question với context
    user_message = RAG_PROMPT_TEMPLATE.format(
        context=context,
        question=question
    )
    messages.append({
        "role": "user",
        "content": user_message
    })

    return messages


# ============================================
# EXPORT
# ============================================

__all__ = [
    'HEALTH_CHATBOT_SYSTEM_PROMPT',
    'RAG_PROMPT_TEMPLATE',
    'GREETING_RESPONSES',
    'FAREWELL_RESPONSES',
    'NO_DOCS_FOUND_RESPONSE',
    'DISCLAIMER_TEXT',
    'format_context',
    'format_sources',
    'is_greeting',
    'is_farewell',
    'build_messages'
]
