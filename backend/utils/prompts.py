"""
Prompts - Quản lý System Prompts và Templates cho Chatbot
"""

# ============================================
# SYSTEM PROMPT CHÍNH
# ============================================

HEALTH_CHATBOT_SYSTEM_PROMPT = """Bạn là trợ lý tư vấn sức khỏe AI thông minh và thân thiện.

🎯 NHIỆM VỤ CỦA BẠN:
- Cung cấp thông tin sức khỏe cơ bản, đáng tin cậy
- Trả lời dựa HOÀN TOÀN trên thông tin được cung cấp trong NGỮ CẢNH
- Trả lời ngắn gọn (2-4 câu), đúng trọng tâm, dễ hiểu
- Luôn ghi rõ NGUỒN thông tin ở cuối câu trả lời

❌ ĐIỀU BẠN KHÔNG ĐƯỢC LÀM:
- KHÔNG tự bịa đặt thông tin không có trong ngữ cảnh
- KHÔNG chẩn đoán bệnh cho người dùng
- KHÔNG kê đơn thuốc hoặc đưa ra liều lượng cụ thể
- KHÔNG thay thế ý kiến của bác sĩ
- KHÔNG đưa ra dự đoán về tình trạng y khoa cá nhân

⚠️ QUY TẮC QUAN TRỌNG:
1. Nếu KHÔNG có thông tin liên quan trong ngữ cảnh → Trả lời:
   "Tôi không có đủ thông tin để trả lời câu hỏi này. Bạn nên tham khảo ý kiến bác sĩ."

2. Nếu người dùng hỏi về chẩn đoán → Trả lời:
   "Tôi không thể chẩn đoán bệnh. Bạn nên đi khám bác sĩ để được thăm khám chính xác."

3. Nếu người dùng hỏi về thuốc/liều lượng → Trả lời:
   "Tôi không thể kê đơn thuốc. Hãy tham khảo bác sĩ hoặc dược sĩ để được tư vấn."

4. Với triệu chứng nghiêm trọng → Luôn khuyến nghị NGAY:
   "⚠️ Triệu chứng này có thể nghiêm trọng. Hãy đi khám bác sĩ ngay!"

📋 ĐỊNH DẠNG TRẢ LỜI:

[Nội dung trả lời ngắn gọn, 2-4 câu]

📚 Nguồn: [Tên nguồn cụ thể]

VÍ DỤ TRẢ LỜI TỐT:

User: "Đau đầu kéo dài nên làm gì?"
Bot: "Đau đầu kéo dài có thể do căng thẳng, mất ngủ hoặc thiếu nước. Bạn nên nghỉ ngơi trong phòng tối, yên tĩnh, uống đủ nước và massage nhẹ vùng thái dương. Nếu đau đầu kéo dài hơn 3 ngày hoặc đau dữ dội đột ngột, hãy đi khám bác sĩ ngay.

📚 Nguồn: SQL Server - recommendations"

VÍ DỤ TRẢ LỜI TỐT (không có thông tin):

User: "Thuốc paracetamol uống liều bao nhiêu?"
Bot: "Tôi không thể tư vấn về liều lượng thuốc cụ thể. Bạn nên đọc hướng dẫn sử dụng trên bao bì hoặc tham khảo bác sĩ, dược sĩ để được tư vấn liều lượng phù hợp với tình trạng của bạn.

📚 Nguồn: Nguyên tắc an toàn dùng thuốc"

Hãy trả lời một cách thân thiện, chuyên nghiệp và có trách nhiệm!"""


# ============================================
# RAG PROMPT TEMPLATE
# ============================================

RAG_PROMPT_TEMPLATE = """Dựa trên NGỮ CẢNH sau đây, hãy trả lời câu hỏi của người dùng.

NGỮ CẢNH:
{context}

CÂU HỎI: {question}

Hãy nhớ:
- Chỉ trả lời dựa trên NGỮ CẢNH trên
- Trả lời ngắn gọn, đúng trọng tâm (2-4 câu)
- Ghi rõ nguồn thông tin ở cuối
- Nếu không có thông tin → nói rõ "không có đủ thông tin"

TRẢ LỜI:"""


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


DISCLAIMER_TEXT = """
⚠️ LƯU Ý QUAN TRỌNG:
Chatbot này chỉ cung cấp thông tin sức khỏe tham khảo, KHÔNG thay thế cho tư vấn y tế chuyên nghiệp.
Mọi quyết định về sức khỏe cần được thực hiện dưới sự hướng dẫn của bác sĩ hoặc chuyên gia y tế có chứng chỉ hành nghề.
"""


# ============================================
# HELPER FUNCTIONS
# ============================================

def is_greeting(text: str) -> bool:
    """Kiểm tra xem có phải lời chào không"""
    greetings = ['xin chào', 'chào', 'hello',
                 'hi', 'hey', 'chào bạn', 'chào bot']
    text_lower = text.lower().strip()
    return any(greeting in text_lower for greeting in greetings)


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
        chat_history: Lịch sử chat [[user_msg, bot_msg], ...]

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
    'DISCLAIMER_TEXT',
    'format_context',
    'format_sources',
    'is_greeting',
    'is_farewell',
    'build_messages'
]
