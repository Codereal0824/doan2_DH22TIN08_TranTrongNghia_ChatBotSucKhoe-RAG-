"""
RAG Chain - Kết hợp Retrieval + Generation
"""
from config.config import config
from backend.utils.prompts import (
    HEALTH_CHATBOT_SYSTEM_PROMPT,
    RAG_PROMPT_TEMPLATE,
    GREETING_RESPONSES,
    FAREWELL_RESPONSES,
    format_context,
    format_sources,
    is_greeting,
    is_farewell,
    build_messages
)
from backend.api.groq_client import GroqClient
from backend.rag.retriever import RAGRetriever
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Generator
import random

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
            print("🔄 Khởi tạo RAG Retriever...")
            self.retriever = RAGRetriever(top_k=self.top_k)

        # Khởi tạo LLM client
        if llm_client:
            self.llm = llm_client
        else:
            print("🔄 Khởi tạo Groq LLM...")
            self.llm = GroqClient()

        print(f"✅ RAG Chain sẵn sàng!")

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

        # Retrieve relevant documents
        retrieved_docs = self.retriever.retrieve(question, top_k=self.top_k)

        # Format context
        context = format_context(retrieved_docs)

        # Build messages
        messages = build_messages(
            question=question,
            context=context,
            system_prompt=HEALTH_CHATBOT_SYSTEM_PROMPT,
            chat_history=chat_history
        )

        # Generate answer
        answer = self.llm.chat(messages)

        # Thêm nguồn nếu cần
        if return_sources and retrieved_docs:
            sources = format_sources(retrieved_docs)
            if sources and "📚 Nguồn:" not in answer:
                answer += f"\n\n📚 Nguồn: {sources}"

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

        # Retrieve
        retrieved_docs = self.retriever.retrieve(question, top_k=self.top_k)

        # Format context
        context = format_context(retrieved_docs)

        # Build messages
        messages = build_messages(
            question=question,
            context=context,
            system_prompt=HEALTH_CHATBOT_SYSTEM_PROMPT,
            chat_history=chat_history
        )

        # Stream response
        for chunk in self.llm.chat_stream(messages):
            yield chunk

        # Thêm nguồn
        if return_sources and retrieved_docs:
            sources = format_sources(retrieved_docs)
            if sources:
                yield f"\n\n📚 Nguồn: {sources}"

    def get_relevant_info(self, question: str, top_k: int = None) -> List[Dict]:
        """
        Chỉ retrieve thông tin, không generate

        Args:
            question: Câu hỏi
            top_k: Số documents

        Returns:
            List[Dict]: Documents liên quan
        """
        k = top_k or self.top_k
        return self.retriever.retrieve(question, top_k=k)


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
            print("🚀 Đang khởi tạo Health Chatbot...")
            self.rag_chain = RAGChain()

        # Chat history: [(user_msg, bot_msg), ...]
        self.chat_history = []

        # Max history turns
        self.max_history_turns = 5

        print(f"✅ Health Chatbot sẵn sàng phục vụ!")

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
        print("🗑️  Đã xóa lịch sử chat")

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
        print(f"\n🤖 Trả lời:")

        answer = rag_chain.ask(question)
        print(answer)

        # Test 2: Streaming
        print("\n" + "=" * 70)
        print("TEST 2 - STREAMING")
        print("=" * 70)

        question = "Đau đầu kéo dài nên làm gì?"
        print(f"\n❓ Câu hỏi: {question}")
        print(f"\n🤖 Trả lời (streaming):")

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
