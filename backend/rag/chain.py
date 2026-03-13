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

        # Khởi tạo retriever
        if retriever:
            self.retriever = retriever
        else:
            logger.info("🔄 Khởi tạo RAG Retriever...")
            self.retriever = RAGRetriever(top_k=self.top_k)

        # Khởi tạo LLM client
        if llm_client:
            self.llm = llm_client
        else:
            logger.info("🔄 Khởi tạo Groq LLM...")
            self.llm = GroqClient()

        logger.info("✅ RAG Chain sẵn sàng!")

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
        # Kiểm tra greeting/farewell
        if is_greeting(question):
            return random.choice(GREETING_RESPONSES)

        if is_farewell(question):
            return random.choice(FAREWELL_RESPONSES)

        # ============================================
        # SAFETY CONTROL: Block medical queries (NEW)
        # ============================================
        should_block, block_reason = should_block_query(question)
        if should_block:
            logger.warning(f"🚫 QUERY BLOCKED: {block_reason}")
            return STRICT_FALLBACK_RESPONSE

        # Retrieve relevant documents với score filtering
        retrieved_docs = self.retriever.retrieve(
            question,
            top_k=self.top_k,
            apply_threshold=True  # Bật filtering
        )

        # ⚠️ KIỂM TRA: Nếu KHÔNG có docs sau filtering → KHÔNG gọi LLM
        if not retrieved_docs or len(retrieved_docs) == 0:
            logger.warning(
                "❌ No documents passed relevance threshold → Returning fallback")
            return NO_DOCS_FOUND_RESPONSE

        # Format context
        context = format_context(retrieved_docs)
        all_sources = format_sources(retrieved_docs)

        # ============================================
        # PRE-LLM GATE 1: FOOD/SUPPLEMENT QUERY CHECK
        # Nếu câu hỏi hỏi về thực phẩm/vitamin có chữa bệnh không
        # mà context không trực tiếp đề cập tới thực phẩm đó → FALLBACK
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
                    f"🍎 Food/supplement '{_matched_food}' not in context → FALLBACK")
                return f"{NO_DOCS_FOUND_RESPONSE}\n\nNguồn: Không có"

        # ============================================
        # PRE-LLM GATE 2: SEMANTIC CONTEXT RELEVANCE
        # Nếu context không liên quan đến câu hỏi → FALLBACK
        # ============================================
        if not check_context_relevance(question, context):
            logger.warning(
                "❌ Context không liên quan đến câu hỏi → FALLBACK")
            return f"{NO_DOCS_FOUND_RESPONSE}\n\nNguồn: Không có"

        # Build messages — pass source filenames so LLM cites only those it uses
        messages = build_messages(
            question=question,
            context=context,
            system_prompt=HEALTH_CHATBOT_SYSTEM_PROMPT,
            chat_history=chat_history,
            sources=all_sources
        )

        # Generate answer với temperature=0 (strict mode)
        try:
            answer = self.llm.chat(messages, temperature=0.0)
        except Exception as e:
            error_str = str(e)
            if 'API_DAILY_LIMIT' in error_str:
                logger.error("❌ Groq daily token quota exhausted")
                return "⚠️ Hệ thống đã hết quota API trong ngày. Vui lòng thử lại vào ngày mai hoặc nâng cấp tài khoản Groq."
            elif 'API_RATE_LIMIT' in error_str:
                logger.error("❌ API rate limit exhausted after retries")
                return "⏳ Hệ thống đang quá tải. Vui lòng thử lại sau vài phút."
            else:
                logger.error(f"❌ LLM Error: {error_str}")
                return "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau."

        # ============================================
        # CAPTURE SOURCES FROM RAW LLM ANSWER
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
        logger.info(f"📎 Raw LLM sources: {_raw_cited} → valid: {_pre_cited}")

        # ============================================
        # POST-GENERATION SAFETY FILTER (CRITICAL)
        # ============================================
        logger.info("🔍 Running post-generation safety check...")
        answer = sanitize_answer(answer)

        # If sanitize_answer returned fallback, return with explicit Nguồn: Không có
        if answer == STRICT_FALLBACK_RESPONSE or answer == NO_DOCS_FOUND_RESPONSE:
            return f"{answer}\n\nNguồn: Không có"

        # ============================================
        # VERIFICATION AI - Validate & Correct Answer
        # ============================================
        logger.info("🤖 Running Verification AI...")
        answer = verify_answer(
            question=question,
            context=context,
            draft_answer=answer
        )

        # ==========================================
        # ✅ FINAL CLEANUP: LÀM ĐẸP TÊN NGUỒN VÀ XÓA RÁC
        # ==========================================
        try:
            parts = re.split(r'\n+Nguồn:\s*', answer, flags=re.IGNORECASE)
            if len(parts) == 2:
                main_text, sources_str = parts

                # Loại bỏ chữ "Tiêm chủng" khỏi nội dung liệt kê bệnh và dọn dẹp dấu phẩy dư
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

                    # Dịch .txt thành tên tiếng Việt có dấu
                    if src.endswith('.txt'):
                        nice_name = _FILENAME_TO_DISEASE.get(
                            src, src.replace('.txt', '').replace('_', ' ').title())
                    else:
                        nice_name = src

                    # Chặn "Tiêm chủng" khỏi danh sách nguồn
                    if nice_name not in nice_sources and nice_name.lower() != 'tiêm chủng':
                        nice_sources.append(nice_name)

                final_sources_str = ', '.join(
                    nice_sources) if nice_sources else "Không có"
                answer = main_text.strip() + f"\n\nNguồn: {final_sources_str}"
        except Exception as e:
            logger.error(f"Error post-processing answer: {e}")

        if config.DEBUG:
            logger.debug(f"✅ Verified Answer: {answer[:200]}...")

        return answer

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
        # Kiểm tra greeting/farewell
        if is_greeting(question):
            yield random.choice(GREETING_RESPONSES)
            return

        if is_farewell(question):
            yield random.choice(FAREWELL_RESPONSES)
            return

        # ============================================
        # SAFETY CONTROL: Block medical queries (NEW)
        # ============================================
        should_block, block_reason = should_block_query(question)
        if should_block:
            logger.warning(f"🚫 QUERY BLOCKED (stream): {block_reason}")
            yield STRICT_FALLBACK_RESPONSE
            return

        # Retrieve với score filtering
        retrieved_docs = self.retriever.retrieve(
            question,
            top_k=self.top_k,
            apply_threshold=True  # Bật filtering
        )

        # ⚠️ KIỂM TRA: Nếu KHÔNG có docs sau filtering → KHÔNG gọi LLM
        if not retrieved_docs or len(retrieved_docs) == 0:
            logger.warning(
                "❌ No documents passed relevance threshold (stream) → Returning fallback")
            yield NO_DOCS_FOUND_RESPONSE
            return

        # Format context
        context = format_context(retrieved_docs)
        all_sources = format_sources(retrieved_docs)

        # ============================================
        # PRE-LLM GATE 1: FOOD/SUPPLEMENT QUERY CHECK (stream)
        # ============================================
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
                    f"🍎 Food/supplement '{_matched_food_s}' not in context (stream) → FALLBACK")
                yield f"{NO_DOCS_FOUND_RESPONSE}\n\nNguồn: Không có"
                return

        # ============================================
        # PRE-LLM GATE 2: SEMANTIC CONTEXT RELEVANCE (stream)
        # ============================================
        if not check_context_relevance(question, context):
            logger.warning(
                "❌ Context không liên quan (stream) → FALLBACK")
            yield f"{NO_DOCS_FOUND_RESPONSE}\n\nNguồn: Không có"
            return

        # Build messages — pass source filenames so LLM cites only those it uses
        messages = build_messages(
            question=question,
            context=context,
            system_prompt=HEALTH_CHATBOT_SYSTEM_PROMPT,
            chat_history=chat_history,
            sources=all_sources
        )

        # ============================================
        # COLLECT FULL RESPONSE FOR SAFETY CHECK
        logger.info("🔄 Generating answer (streaming mode)...")
        full_answer = ""

        # Stream and collect response với temperature=0 (strict mode)
        try:
            for chunk in self.llm.chat_stream(messages, temperature=0.0):
                full_answer += chunk
        except Exception as e:
            error_str = str(e)
            if 'API_DAILY_LIMIT' in error_str:
                logger.error("❌ Groq daily quota exhausted (stream)")
                yield "⚠️ Hệ thống đã hết quota API trong ngày. Vui lòng thử lại vào ngày mai hoặc nâng cấp tài khoản Groq."
            elif 'API_RATE_LIMIT' in error_str:
                logger.error("❌ API rate limit exhausted (stream)")
                yield "⏳ Hệ thống đang quá tải. Vui lòng thử lại sau vài phút."
            else:
                logger.error(f"❌ LLM Error (stream): {error_str}")
                yield "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau."
            return

        # ============================================
        # CAPTURE SOURCES FROM RAW LLM ANSWER (stream)
        # ============================================
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
            f"📎 Raw LLM sources (stream): {_raw_cited_s} → valid: {_pre_cited_s}")

        # ============================================
        # POST-GENERATION SAFETY FILTER (CRITICAL)
        # ============================================
        logger.info("🔍 Running post-generation safety check (stream)...")
        full_answer = sanitize_answer(full_answer)

        # If sanitize_answer returned fallback, yield with explicit Nguồn: Không có
        if full_answer == STRICT_FALLBACK_RESPONSE or full_answer == NO_DOCS_FOUND_RESPONSE:
            yield f"{full_answer}\n\nNguồn: Không có"
            return

        # ============================================
        # VERIFICATION AI - Validate & Correct Answer
        # ============================================
        logger.info("🤖 Running Verification AI (stream)...")
        full_answer = verify_answer(
            question=question,
            context=context,
            draft_answer=full_answer
        )

        # ==========================================
        # ✅ FINAL CLEANUP: LÀM ĐẸP TÊN NGUỒN VÀ XÓA RÁC
        # ==========================================
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
            logger.debug(f"✅ Verified Answer (stream): {full_answer[:200]}...")

        # Yield the verified answer
        yield full_answer

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
            logger.info("🚀 Đang khởi tạo Health Chatbot...")
            self.rag_chain = RAGChain()

        # Chat history: [(user_msg, bot_msg), ...]
        self.chat_history = []

        # Max history turns
        self.max_history_turns = 5

        logger.info("✅ Health Chatbot sẵn sàng phục vụ!")

    def chat(self, user_message: str) -> str:
        """
        Chat với bot (có lưu history)

        Args:
            user_message: Tin nhắn từ user

        Returns:
            str: Phản hồi
        """
        # Generate response
        bot_response = self.rag_chain.ask(
            question=user_message,
            chat_history=self.chat_history,
            return_sources=True
        )

        # Lưu vào history
        self.chat_history.append((user_message, bot_response))

        # Giới hạn history
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

        # Lưu history
        self.chat_history.append((user_message, full_response))

        # Giới hạn
        if len(self.chat_history) > self.max_history_turns:
            self.chat_history = self.chat_history[-self.max_history_turns:]

    def clear_history(self):
        """Xóa lịch sử chat"""
        self.chat_history = []
        logger.info("🗑️  Đã xóa lịch sử chat")

    def get_history(self) -> List[Tuple[str, str]]:
        """Lấy lịch sử chat"""
        return self.chat_history.copy()


def demo_rag_chain():
    """Demo RAG Chain"""
    print("=" * 70)
    print("DEMO - RAG CHAIN")
    print("=" * 70)

    try:
        # Tạo RAG Chain
        rag_chain = RAGChain()

        # Test 1: Simple ask
        print("\n" + "=" * 70)
        print("TEST 1 - SIMPLE ASK")
        print("=" * 70)

        question = "Triệu chứng cảm cúm là gì?"
        print(f"\n❓ Câu hỏi: {question}")
        print("\n🤖 Trả lời:")

        answer = rag_chain.ask(question)
        print(answer)

        # Test 2: Streaming
        print("\n" + "=" * 70)
        print("TEST 2 - STREAMING")
        print("=" * 70)

        question = "Đau đầu kéo dài nên làm gì?"
        print(f"\n❓ Câu hỏi: {question}")
        print("\n🤖 Trả lời (streaming):")

        for chunk in rag_chain.ask_stream(question):
            print(chunk, end='', flush=True)

        print("\n")

        # Test 3: Chatbot với history
        print("\n" + "=" * 70)
        print("TEST 3 - CHATBOT VỚI MEMORY")
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
            print(f"\n👤 User: {user_msg}")
            bot_response = chatbot.chat(user_msg)
            print(f"🤖 Bot: {bot_response}")

        print(f"\n📊 Lịch sử: {len(chatbot.get_history())} turns")

        print("\n✅ Demo hoàn tất!")

    except ValueError as e:
        print(f"\n{e}")


if __name__ == "__main__":
    demo_rag_chain()
