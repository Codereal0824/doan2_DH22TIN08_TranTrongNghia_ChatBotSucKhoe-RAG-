"""
RAG Chain - Kết hợp Retrieval + Generation
"""
from config.config import config
from backend.rag.prompts import (
    HEALTH_CHATBOT_SYSTEM_PROMPT,
    GREETING_RESPONSES,
    FAREWELL_RESPONSES,
    NO_DOCS_FOUND_RESPONSE,
    STRICT_FALLBACK_RESPONSE,
    format_context,
    format_sources,
    is_greeting,
    is_farewell,
    build_messages,
    sanitize_answer,
    verify_answer,
    check_context_relevance,    # Pre-LLM relevance gate
    extract_sources_from_answer,  # Source extraction from LLM answer
    extract_sources_from_context,  # Source extraction from retrieved context
)
from backend.utils.query_normalizer import should_block_query
from backend.api.groq_client import GroqClient
from backend.rag.retriever import RAGRetriever
from backend.utils.logger import get_logger
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Generator
import random

logger = get_logger(__name__)

# Import modules
sys.path.append(str(Path(__file__).parent.parent.parent))

# Lớp RAGChain đóng vai trò là Bộ điều phối trung tâm (Orchestrator).
# Nó kết hợp mô-đun Truy xuất (Retriever) và mô-đun Sinh văn bản (Generator/LLM),
# đồng thời áp dụng hàng loạt các cổng kiểm duyệt (Safety Gates) trước và sau khi gọi AI.


class RAGChain:
    """RAG Chain kết hợp Retrieval và Generation"""

    def __init__(
        self,
        retriever: RAGRetriever = None,
        llm_client: GroqClient = None,
        top_k: int = None
    ):
        """
        Khởi tạo RAG Chain

        Args:
            retriever: RAG Retriever instance
            llm_client: Groq Client instance
            top_k: Số documents retrieve
        """
        self.top_k = top_k or config.TOP_K_RETRIEVAL

        # Khởi tạo mô-đun truy xuất (Hybrid Search Retriever)
        if retriever:
            self.retriever = retriever
        else:
            logger.info("Khoi tao RAG Retriever...")
            self.retriever = RAGRetriever(top_k=self.top_k)

        # Khởi tạo mô-đun LLM (Groq Client)
        if llm_client:
            self.llm = llm_client
        else:
            logger.info("Khoi tao Groq LLM...")
            self.llm = GroqClient()

        logger.info("RAG Chain san sang!")

    # Hàm thực thi luồng RAG cơ bản (Đồng bộ).
    # Áp dụng cơ chế kiểm duyệt đa lớp nghiêm ngặt để đảm bảo an toàn y khoa.
    def ask(
        self,
        question: str,
        chat_history: List[Tuple[str, str]] = None,
        return_sources: bool = True
    ) -> str:
        """
        Hỏi đáp với RAG

        Args:
            question: Câu hỏi
            chat_history: Lịch sử chat [(user_msg, bot_msg), ...]
            return_sources: Có trả về nguồn không

        Returns:
            str: Câu trả lời
        """
        # BƯỚC 1: Xử lý ý định giao tiếp cơ bản (Intent Matching).
        # Tiết kiệm tài nguyên API bằng cách trả lời ngay các câu chào hỏi/tạm biệt.
        if is_greeting(question):
            return random.choice(GREETING_RESPONSES)

        if is_farewell(question):
            return random.choice(FAREWELL_RESPONSES)

        # ============================================
        # BƯỚC 2: CỔNG AN TOÀN SỐ 1 (SAFETY CONTROL)
        # Sử dụng Query Normalizer để chặn đứng các yêu cầu vi phạm đạo đức y tế
        # (như yêu cầu kê đơn thuốc, chẩn đoán bệnh lâm sàng) ngay từ đầu.
        # ============================================
        should_block, block_reason = should_block_query(question)
        if should_block:
            logger.warning(f"QUERY BLOCKED: {block_reason}")
            return STRICT_FALLBACK_RESPONSE

        # BƯỚC 3: Truy xuất tài liệu (Retrieval) tích hợp màng lọc ngưỡng (Threshold Filtering).
        # Chỉ những tài liệu có điểm số RRF vượt ngưỡng mới được giữ lại.
        retrieved_docs = self.retriever.retrieve(
            question,
            top_k=self.top_k,
            apply_threshold=True  # Bật filtering
        )

        # KIỂM TRA MỨC ĐỘ TỒN TẠI TÀI LIỆU
        # Nếu không có tài liệu nào vượt qua ngưỡng, hệ thống kích hoạt Fallback
        # thay vì để LLM tự "ảo giác" (hallucinate) ra câu trả lời.
        if not retrieved_docs or len(retrieved_docs) == 0:
            logger.warning(
                "No documents passed relevance threshold -> Returning fallback")
            return NO_DOCS_FOUND_RESPONSE

        # Định dạng ngữ cảnh (Context) và Nguồn (Sources) để chèn vào Prompt
        context = format_context(retrieved_docs)
        all_sources = format_sources(retrieved_docs)

        # ============================================
        # BƯỚC 4: CỔNG AN TOÀN SỐ 2 (FOOD/SUPPLEMENT GATE)
        # Giải quyết triệt để lỗi AI khuyên dùng thực phẩm để "chữa bệnh".
        # Nếu câu hỏi nhắc đến việc chữa bệnh bằng thực phẩm, hệ thống sẽ dò quét
        # xem ngữ cảnh (Context) có thực sự xác nhận điều đó không. Nếu không -> Chặn!
        # ============================================
        _FOOD_SUPPLEMENT_TERMS = [
            'vitamin c', 'vitamin d', 'vitamin a', 'vitamin e',
            'vitamin b1', 'vitamin b2', 'vitamin b6', 'vitamin b12',
            'sầu riêng', 'mật ong', 'gừng', 'tỏi', 'nghệ',
            'dầu cá', 'omega-3', 'omega 3', 'canxi', 'kẽm',
            'magiê', 'collagen', 'probiotic', 'men vi sinh',
            'nha đam', 'trà xanh', 'cà phê', 'chanh', 'bưởi',
        ]
        _CURE_VERBS = ['chữa', 'trị bệnh', 'trị được', 'chữa được',
                       'chữa bệnh', 'phòng bệnh', 'phòng ngừa bệnh']
        _q_lower = question.lower()
        _matched_food = next(
            (f for f in _FOOD_SUPPLEMENT_TERMS if f in _q_lower), None)
        if _matched_food and any(v in _q_lower for v in _CURE_VERBS):
            if _matched_food not in context.lower():
                logger.info(
                    f"Food/supplement '{_matched_food}' not in context -> FALLBACK")
                return f"{NO_DOCS_FOUND_RESPONSE}\n\nNguồn: Không có"

        # ============================================
        # BƯỚC 5: CỔNG AN TOÀN SỐ 3 (SEMANTIC CONTEXT RELEVANCE)
        # Đánh giá chéo mức độ liên quan ngữ nghĩa giữa Câu hỏi và Ngữ cảnh.
        # ============================================
        if not check_context_relevance(question, context):
            logger.warning(
                "Context khong lien quan den cau hoi -> FALLBACK")
            return f"{NO_DOCS_FOUND_RESPONSE}\n\nNguồn: Không có"

        # Đóng gói Prompt hoàn chỉnh gồm: Chỉ thị hệ thống, Lịch sử, Ngữ cảnh và Câu hỏi.
        messages = build_messages(
            question=question,
            context=context,
            system_prompt=HEALTH_CHATBOT_SYSTEM_PROMPT,
            chat_history=chat_history,
            sources=all_sources
        )

        # ============================================
        # BƯỚC 6: SINH VĂN BẢN (GENERATION)
        # Thiết lập temperature=0.0 (Chế độ Strict/Deterministic)
        # để buộc LLM trả lời dựa trên facts (sự thật), triệt tiêu sự sáng tạo tự do.
        # ============================================
        try:
            answer = self.llm.chat(messages, temperature=0.0)
        except Exception as e:
            error_str = str(e)
            if 'API_DAILY_LIMIT' in error_str:
                logger.error("Groq daily token quota exhausted")
                return "Hệ thống đã hết quota API trong ngày. Vui lòng thử lại vào ngày mai hoặc nâng cấp tài khoản Groq."
            elif 'API_RATE_LIMIT' in error_str:
                logger.error("API rate limit exhausted after retries")
                return "Hệ thống đang quá tải. Vui lòng thử lại sau vài phút."
            else:
                logger.error(f"LLM Error: {error_str}")
                return "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau."

        # ============================================
        # BƯỚC 7: TRÍCH XUẤT VÀ ĐỐI CHIẾU NGUỒN (SOURCE GROUNDING)
        # Kiểm tra xem các nguồn do LLM sinh ra có thực sự nằm trong danh sách
        # ngữ cảnh đã cung cấp ban đầu hay không.
        # ============================================
        _sources_in_context = extract_sources_from_context(context)
        _raw_cited = extract_sources_from_answer(answer)
        _MEDICAL_ANCHORS = [
            'stress', 'lo âu', 'mất ngủ', 'gout', 'sốt xuất huyết', 'cúm',
            'covid', 'đái tháo đường', 'béo phì', 'đau khớp', 'đau đầu',
            'mệt mỏi', 'buồn nôn', 'chóng mặt', 'tim', 'tim mạch', 'huyết áp',
            'tiêu hóa', 'viêm họng', 'hen', 'trầm cảm',
        ]
        _anchor_terms = [a for a in _MEDICAL_ANCHORS if a in question.lower()]

        def _source_is_relevant(src: str) -> bool:
            """Kiểm tra chunk của source trong context có chứa ít nhất 1 topic word."""
            src_pattern = re.escape(src)
            chunk_match = re.search(
                rf'\[Tài liệu \d+ - {src_pattern}(?:\s*\|[^\]]*)?\](.+?)(?=\[Tài liệu|$)',
                context, re.DOTALL)
            if not chunk_match:
                return True
            chunk_text = chunk_match.group(1).lower()
            if not _anchor_terms:
                return True
            return any(a in chunk_text for a in _anchor_terms)

        _pre_cited = [
            s for s in _raw_cited
            if s in _sources_in_context and _source_is_relevant(s)
        ][:3]
        logger.info(f"Raw LLM sources: {_raw_cited} -> valid: {_pre_cited}")

        # ============================================
        # BƯỚC 8: CỔNG AN TOÀN SỐ 4 - KIỂM DUYỆT HẬU KỲ (POST-GENERATION SAFETY FILTER)
        # Cắt gọt và làm sạch câu trả lời, đảm bảo không vi phạm quy tắc hệ thống.
        # ============================================
        logger.info("Running post-generation safety check...")
        answer = sanitize_answer(answer)

        # Nếu quy trình sanitize quyết định đây là câu trả lời Fallback, đính kèm nguồn trống.
        if answer == STRICT_FALLBACK_RESPONSE or answer == NO_DOCS_FOUND_RESPONSE:
            return f"{answer}\n\nNguồn: Không có"

        # ============================================
        # BƯỚC 9: CỔNG AN TOÀN SỐ 5 - VERIFICATION AI (GIÁM ĐỊNH VIÊN AI)
        # Một luồng AI độc lập khác sẽ được gọi để đọc lại câu trả lời vừa sinh ra.
        # Nếu phát hiện câu trả lời chứa thông tin y tế nằm ngoài ngữ cảnh -> Hủy kết quả.
        # ============================================
        logger.info("Running Verification AI...")
        answer = verify_answer(
            question=question,
            context=context,
            draft_answer=answer
        )

        # ==========================================
        # BƯỚC 10: LÀM SẠCH BỀ MẶT BẰNG REGEX (FINAL CLEANUP)
        # Chuẩn hóa định dạng chuỗi trước khi hiển thị lên giao diện Web.
        # ==========================================
        try:
            parts = re.split(r'\n+Nguồn:\s*', answer, flags=re.IGNORECASE)
            if len(parts) == 2:
                main_text, sources_str = parts

                # Loại bỏ từ khóa nhạy cảm "Tiêm chủng" khỏi danh sách liệt kê và dọn dẹp dấu câu
                main_text = re.sub(r'(?i)tiêm\s*chủng', '', main_text)
                main_text = re.sub(r'\s*,\s*,', ',', main_text)
                main_text = re.sub(r':\s*,', ':', main_text)
                main_text = re.sub(r',\s*\.', '.', main_text)
                main_text = re.sub(r'\s+', ' ', main_text).strip()

                from backend.rag.prompts import _FILENAME_TO_DISEASE
                nice_sources = []
                for src in sources_str.split(','):
                    src = src.strip()
                    if src.lower() == 'không có' or not src:
                        if 'Không có' not in nice_sources:
                            nice_sources.append('Không có')
                        continue

                    # Ánh xạ tên file (.txt) thành tên bệnh tiếng Việt có dấu để giao diện thân thiện hơn
                    if src.endswith('.txt'):
                        nice_name = _FILENAME_TO_DISEASE.get(
                            src, src.replace('.txt', '').replace('_', ' ').title())
                    else:
                        nice_name = src

                    # Bộ lọc cuối: Chặn "Tiêm chủng" xuất hiện trong danh sách nguồn hiển thị
                    if nice_name not in nice_sources and nice_name.lower() != 'tiêm chủng':
                        nice_sources.append(nice_name)

                final_sources_str = ', '.join(
                    nice_sources) if nice_sources else "Không có"
                answer = main_text.strip() + f"\n\nNguồn: {final_sources_str}"
        except Exception as e:
            logger.error(f"Error post-processing answer: {e}")

        if config.DEBUG:
            logger.debug(f"Verified Answer: {answer[:200]}...")

        return answer

    # Hàm thực thi luồng RAG dạng Streaming (Truyền phát liên tục).
    # Logic bên trong phản chiếu lại toàn bộ 10 bước của hàm ask() đồng bộ ở trên,
    # nhưng sử dụng từ khóa 'yield' để hỗ trợ Server-Sent Events (SSE) về phía Client.
    def ask_stream(
        self,
        question: str,
        chat_history: List[Tuple[str, str]] = None,
        return_sources: bool = True
    ) -> Generator[str, None, None]:
        """
        Hỏi đáp với streaming response

        Args:
            question: Câu hỏi
            chat_history: Lịch sử chat
            return_sources: Trả về nguồn

        Yields:
            str: Từng phần câu trả lời
        """
        if is_greeting(question):
            yield random.choice(GREETING_RESPONSES)
            return

        if is_farewell(question):
            yield random.choice(FAREWELL_RESPONSES)
            return

        should_block, block_reason = should_block_query(question)
        if should_block:
            logger.warning(f"QUERY BLOCKED (stream): {block_reason}")
            yield STRICT_FALLBACK_RESPONSE
            return

        retrieved_docs = self.retriever.retrieve(
            question,
            top_k=self.top_k,
            apply_threshold=True
        )

        if not retrieved_docs or len(retrieved_docs) == 0:
            logger.warning(
                "No documents passed relevance threshold (stream) -> Returning fallback")
            yield NO_DOCS_FOUND_RESPONSE
            return

        context = format_context(retrieved_docs)
        all_sources = format_sources(retrieved_docs)

        _FOOD_SUPPLEMENT_TERMS_S = [
            'vitamin c', 'vitamin d', 'vitamin a', 'vitamin e',
            'vitamin b1', 'vitamin b2', 'vitamin b6', 'vitamin b12',
            'sầu riêng', 'mật ong', 'gừng', 'tỏi', 'nghệ',
            'dầu cá', 'omega-3', 'omega 3', 'canxi', 'kẽm',
            'magiê', 'collagen', 'probiotic', 'men vi sinh',
            'nha đam', 'trà xanh', 'cà phê', 'chanh', 'bưởi',
        ]
        _CURE_VERBS_S = ['chữa', 'trị bệnh', 'trị được', 'chữa được',
                         'chữa bệnh', 'phòng bệnh', 'phòng ngừa bệnh']
        _q_lower_s = question.lower()
        _matched_food_s = next(
            (f for f in _FOOD_SUPPLEMENT_TERMS_S if f in _q_lower_s), None)
        if _matched_food_s and any(v in _q_lower_s for v in _CURE_VERBS_S):
            if _matched_food_s not in context.lower():
                logger.info(
                    f"Food/supplement '{_matched_food_s}' not in context (stream) -> FALLBACK")
                yield f"{NO_DOCS_FOUND_RESPONSE}\n\nNguồn: Không có"
                return

        if not check_context_relevance(question, context):
            logger.warning(
                "Context khong lien quan (stream) -> FALLBACK")
            yield f"{NO_DOCS_FOUND_RESPONSE}\n\nNguồn: Không có"
            return

        messages = build_messages(
            question=question,
            context=context,
            system_prompt=HEALTH_CHATBOT_SYSTEM_PROMPT,
            chat_history=chat_history,
            sources=all_sources
        )

        logger.info("Generating answer (streaming mode)...")
        full_answer = ""

        # Ghi nhận dần kết quả sinh ra từ Generator để xử lý hậu kỳ
        try:
            for chunk in self.llm.chat_stream(messages, temperature=0.0):
                full_answer += chunk
        except Exception as e:
            error_str = str(e)
            if 'API_DAILY_LIMIT' in error_str:
                logger.error("Groq daily quota exhausted (stream)")
                yield "Hệ thống đã hết quota API trong ngày. Vui lòng thử lại vào ngày mai hoặc nâng cấp tài khoản Groq."
            elif 'API_RATE_LIMIT' in error_str:
                logger.error("API rate limit exhausted (stream)")
                yield "Hệ thống đang quá tải. Vui lòng thử lại sau vài phút."
            else:
                logger.error(f"LLM Error (stream): {error_str}")
                yield "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau."
            return

        _sources_in_context_s = extract_sources_from_context(context)
        _raw_cited_s = extract_sources_from_answer(full_answer)
        _MEDICAL_ANCHORS_S = [
            'stress', 'lo âu', 'mất ngủ', 'gout', 'sốt xuất huyết', 'cúm',
            'covid', 'đái tháo đường', 'béo phì', 'đau khớp', 'đau đầu',
            'mệt mỏi', 'buồn nôn', 'chóng mặt', 'tim', 'tim mạch', 'huyết áp',
            'tiêu hóa', 'viêm họng', 'hen', 'trầm cảm',
        ]
        _anchor_terms_s = [
            a for a in _MEDICAL_ANCHORS_S if a in question.lower()]

        def _source_is_relevant_s(src: str) -> bool:
            src_pattern = re.escape(src)
            chunk_match_s = re.search(
                rf'\[Tài liệu \d+ - {src_pattern}(?:\s*\|[^\]]*)?\](.+?)(?=\[Tài liệu|$)',
                context, re.DOTALL)
            if not chunk_match_s:
                return True
            chunk_text_s = chunk_match_s.group(1).lower()
            if not _anchor_terms_s:
                return True
            return any(a in chunk_text_s for a in _anchor_terms_s)

        _pre_cited_s = [
            s for s in _raw_cited_s
            if s in _sources_in_context_s and _source_is_relevant_s(s)
        ][:3]
        logger.info(
            f"Raw LLM sources (stream): {_raw_cited_s} -> valid: {_pre_cited_s}")

        logger.info("Running post-generation safety check (stream)...")
        full_answer = sanitize_answer(full_answer)

        if full_answer == STRICT_FALLBACK_RESPONSE or full_answer == NO_DOCS_FOUND_RESPONSE:
            yield f"{full_answer}\n\nNguồn: Không có"
            return

        logger.info("Running Verification AI (stream)...")
        full_answer = verify_answer(
            question=question,
            context=context,
            draft_answer=full_answer
        )

        try:
            parts = re.split(r'\n+Nguồn:\s*', full_answer, flags=re.IGNORECASE)
            if len(parts) == 2:
                main_text, sources_str = parts

                main_text = re.sub(r'(?i)tiêm\s*chủng', '', main_text)
                main_text = re.sub(r'\s*,\s*,', ',', main_text)
                main_text = re.sub(r':\s*,', ':', main_text)
                main_text = re.sub(r',\s*\.', '.', main_text)
                main_text = re.sub(r'\s+', ' ', main_text).strip()

                from backend.rag.prompts import _FILENAME_TO_DISEASE
                nice_sources = []
                for src in sources_str.split(','):
                    src = src.strip()
                    if src.lower() == 'không có' or not src:
                        if 'Không có' not in nice_sources:
                            nice_sources.append('Không có')
                        continue

                    if src.endswith('.txt'):
                        nice_name = _FILENAME_TO_DISEASE.get(
                            src, src.replace('.txt', '').replace('_', ' ').title())
                    else:
                        nice_name = src

                    if nice_name not in nice_sources and nice_name.lower() != 'tiêm chủng':
                        nice_sources.append(nice_name)

                final_sources_str = ', '.join(
                    nice_sources) if nice_sources else "Không có"
                full_answer = main_text.strip(
                ) + f"\n\nNguồn: {final_sources_str}"
        except Exception as e:
            logger.error(f"Error post-processing answer (stream): {e}")

        if config.DEBUG:
            logger.debug(f"Verified Answer (stream): {full_answer[:200]}...")

        # Đẩy toàn bộ khối văn bản đã được kiểm duyệt về lại hàm gọi
        yield full_answer

    # Hàm tiện ích chỉ dùng để trích xuất Context (dùng cho phân tích/debug)
    def get_relevant_info(self, question: str, top_k: int = None, apply_threshold: bool = True) -> List[Dict]:
        """
        Chỉ retrieve thông tin, không generate

        Args:
            question: Câu hỏi
            top_k: Số documents
            apply_threshold: Áp dụng filtering

        Returns:
            List[Dict]: Documents liên quan
        """
        k = top_k or self.top_k
        return self.retriever.retrieve(question, top_k=k, apply_threshold=apply_threshold)

# Lớp HealthChatbot là một Wrapper chuyên quản lý Trạng thái (Stateful).
# Nó bao bọc lấy RAGChain vô trạng thái (Stateless) và cung cấp thêm tính năng
# duy trì Ngữ cảnh Hội thoại (Conversational Memory) qua nhiều lượt chat.


class HealthChatbot:
    """Chatbot hoàn chỉnh với memory"""

    def __init__(self, rag_chain: RAGChain = None):
        """
        Khởi tạo Chatbot

        Args:
            rag_chain: RAG Chain instance
        """
        if rag_chain:
            self.rag_chain = rag_chain
        else:
            logger.info("Dang khoi tao Health Chatbot...")
            self.rag_chain = RAGChain()

        # Cấu trúc lưu trữ lịch sử: Danh sách các Tuple chứa (câu hỏi user, câu trả lời bot)
        self.chat_history = []

        # Cơ chế Cửa sổ trượt (Sliding Window Memory).
        # Giới hạn số lượt hội thoại lưu trữ ở mức 5 để ngăn chặn việc tràn Context Window
        # của LLM và tối ưu hóa chi phí token.
        self.max_history_turns = 5

        logger.info("Health Chatbot san sang phuc vu!")

    def chat(self, user_message: str) -> str:
        """
        Chat với bot (có lưu history)

        Args:
            user_message: Tin nhắn từ user

        Returns:
            str: Phản hồi
        """
        # Gọi RAG Pipeline và truyền kèm lịch sử để duy trì mạch truyện
        bot_response = self.rag_chain.ask(
            question=user_message,
            chat_history=self.chat_history,
            return_sources=True
        )

        # Lưu lượt chat hiện tại vào bộ nhớ
        self.chat_history.append((user_message, bot_response))

        # Áp dụng cơ chế cửa sổ trượt: Chỉ giữ lại N lượt chat mới nhất
        if len(self.chat_history) > self.max_history_turns:
            self.chat_history = self.chat_history[-self.max_history_turns:]

        return bot_response

    def chat_stream(self, user_message: str) -> Generator[str, None, None]:
        """
        Chat với streaming response

        Args:
            user_message: Tin nhắn

        Yields:
            str: Từng phần response
        """
        full_response = ""

        # Stream response
        for chunk in self.rag_chain.ask_stream(
            question=user_message,
            chat_history=self.chat_history,
            return_sources=True
        ):
            full_response += chunk
            yield chunk

        # Sau khi stream hoàn tất chuỗi văn bản, tiến hành lưu vào bộ nhớ
        self.chat_history.append((user_message, full_response))

        if len(self.chat_history) > self.max_history_turns:
            self.chat_history = self.chat_history[-self.max_history_turns:]

    def clear_history(self):
        """Xóa lịch sử chat"""
        self.chat_history = []
        logger.info("Da xoa lich su chat")

    def get_history(self) -> List[Tuple[str, str]]:
        """Lấy lịch sử chat"""
        return self.chat_history.copy()

# Khối lệnh kiểm thử (Unit test)


def demo_rag_chain():
    """Demo RAG Chain"""
    print("=" * 70)
    print("DEMO - RAG CHAIN")
    print("=" * 70)

    try:
        rag_chain = RAGChain()

        print("\n" + "=" * 70)
        print("TEST 1 - SIMPLE ASK")
        print("=" * 70)

        question = "Triệu chứng cảm cúm là gì?"
        print(f"\n Cau hoi: {question}")
        print("\n Tra loi:")

        answer = rag_chain.ask(question)
        print(answer)

        print("\n" + "=" * 70)
        print("TEST 2 - STREAMING")
        print("=" * 70)

        question = "Đau đầu kéo dài nên làm gì?"
        print(f"\n Cau hoi: {question}")
        print("\n Tra loi (streaming):")

        for chunk in rag_chain.ask_stream(question):
            print(chunk, end='', flush=True)

        print("\n")

        print("\n" + "=" * 70)
        print("TEST 3 - CHATBOT VOI MEMORY")
        print("=" * 70)

        chatbot = HealthChatbot(rag_chain)

        conversation = [
            "Xin chào!",
            "Tôi bị sốt và đau đầu",
            "Tôi nên làm gì?",
            "Khi nào cần đi bác sĩ?",
            "Cảm ơn nhé!"
        ]

        for user_msg in conversation:
            print(f"\n User: {user_msg}")
            bot_response = chatbot.chat(user_msg)
            print(f" Bot: {bot_response}")

        print(f"\n Lich su: {len(chatbot.get_history())} turns")

        print("\n Demo hoan tat!")

    except ValueError as e:
        print(f"\n{e}")


if __name__ == "__main__":
    demo_rag_chain()
