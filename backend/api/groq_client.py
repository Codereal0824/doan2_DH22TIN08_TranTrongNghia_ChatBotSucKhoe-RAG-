"""
Groq API Client - Kết nối và sử dụng Groq LLM
"""
from config.config import config
from groq import Groq
from typing import List, Dict, Optional, Generator
import sys
import time
import re
from pathlib import Path
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Import config
sys.path.append(str(Path(__file__).parent.parent.parent))


class GroqClient:
    """Class quản lý Groq API"""

    def __init__(self, api_key: str = None, model: str = None):
        """
        Khởi tạo Groq client

        Args:
            api_key: Groq API key (nếu None sẽ lấy từ config)
            model: Tên model (nếu None sẽ lấy từ config hoặc dùng llama-3.3-70b-versatile)
        """
        self.api_key = api_key or config.GROQ_API_KEY
        self.model = model or config.GROQ_MODEL or "llama-3.3-70b-versatile"

        if not self.api_key:
            raise ValueError(
                "❌ GROQ_API_KEY chưa được cấu hình!\n"
                "💡 Lấy API key miễn phí tại: https://console.groq.com\n"
                "   Sau đó thêm vào file config/.env"
            )

        self.client = Groq(api_key=self.api_key)
        logger.info(f"✅ Groq Client khởi tạo thành công!")
        logger.info(f"📌 Model: {self.model}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None,
        stream: bool = False
    ) -> str:
        """
        Gửi chat request đến Groq API

        Args:
            messages: List of message dicts [{"role": "user", "content": "..."}]
            temperature: Mức độ sáng tạo (0-2)
            max_tokens: Số token tối đa
            stream: Streaming response hay không

        Returns:
            str: Phản hồi từ LLM
        """
        temp = temperature if temperature is not None else config.TEMPERATURE
        tokens = max_tokens if max_tokens is not None else config.MAX_TOKENS

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temp,
                    max_tokens=tokens,
                    stream=stream
                )

                if stream:
                    return response  # Return generator for streaming
                else:
                    return response.choices[0].message.content

            except Exception as e:
                error_str = str(e)
                # Check for rate limit (429)
                if '429' in error_str or 'rate_limit' in error_str:
                    # Daily token limit (TPD) → fail immediately, no retry
                    if 'tokens per day' in error_str.lower() or 'TPD' in error_str:
                        logger.error("❌ Daily token quota exhausted (TPD). Cannot retry.")
                        raise Exception("API_DAILY_LIMIT")
                    # Short rate limit → retry with backoff
                    wait_time = self._parse_retry_after(
                        error_str, default=10 * (attempt + 1))
                    if wait_time > 30:
                        logger.error(
                            f"❌ Rate limit wait too long ({wait_time}s). Failing fast.")
                        raise Exception("API_RATE_LIMIT")
                    logger.warning(
                        f"⏳ Rate limit hit (attempt {attempt+1}/{max_retries}). Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"❌ Lỗi Groq API: {e}")
                    raise  # Re-raise non-rate-limit errors

        # All retries exhausted
        logger.error("❌ Groq API rate limit - all retries exhausted")
        raise Exception("API_RATE_LIMIT")

    @staticmethod
    def _parse_retry_after(error_msg: str, default: int = 15) -> int:
        """Parse wait time from Groq rate limit error message"""
        # Match seconds only (e.g. "3.5s")
        match = re.search(r'Please try again in (\d+\.?\d*)s\.?$', error_msg)
        if match:
            return int(float(match.group(1))) + 2  # Add 2s buffer
        # Match Xm or XmYs format
        match = re.search(r'Please try again in (\d+)m', error_msg)
        if match:
            return int(match.group(1)) * 60
        return default

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None
    ) -> Generator[str, None, None]:
        """
        Streaming chat (trả lời từng từ một)

        Args:
            messages: List of messages
            temperature: Temperature
            max_tokens: Max tokens

        Yields:
            str: Từng phần của response
        """
        temp = temperature if temperature is not None else config.TEMPERATURE
        tokens = max_tokens if max_tokens is not None else config.MAX_TOKENS

        max_retries = 3
        for attempt in range(max_retries):
            try:
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temp,
                    max_tokens=tokens,
                    stream=True
                )

                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return  # Success, exit retry loop

            except Exception as e:
                error_str = str(e)
                if '429' in error_str or 'rate_limit' in error_str:
                    # Daily token limit (TPD) → fail immediately
                    if 'tokens per day' in error_str.lower() or 'TPD' in error_str:
                        logger.error("❌ Daily token quota exhausted (TPD). Cannot retry.")
                        raise Exception("API_DAILY_LIMIT")
                    wait_time = self._parse_retry_after(
                        error_str, default=10 * (attempt + 1))
                    if wait_time > 30:
                        logger.error(
                            f"❌ Rate limit wait too long ({wait_time}s). Failing fast.")
                        raise Exception("API_RATE_LIMIT")
                    logger.warning(
                        f"⏳ Rate limit hit (stream, attempt {attempt+1}/{max_retries}). Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise

        # All retries exhausted
        raise Exception("API_RATE_LIMIT")

    def simple_ask(
        self,
        question: str,
        system_prompt: str = None
    ) -> str:
        """
        Hỏi đáp đơn giản

        Args:
            question: Câu hỏi
            system_prompt: System prompt (optional)

        Returns:
            str: Câu trả lời
        """
        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        messages.append({
            "role": "user",
            "content": question
        })

        return self.chat(messages)

    def get_available_models(self) -> List[str]:
        """Lấy danh sách models có sẵn"""
        try:
            models = self.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            logger.error(f"❌ Lỗi lấy danh sách models: {e}")
            return []

    def get_model_info(self) -> Dict:
        """Lấy thông tin về model đang dùng"""
        return {
            'model': self.model,
            'api_provider': 'Groq',
            'temperature': config.TEMPERATURE,
            'max_tokens': config.MAX_TOKENS
        }


def demo_groq_client():
    """Demo Groq API"""
    print("=" * 70)
    print("DEMO - GROQ API CLIENT")
    print("=" * 70)

    try:
        # Tạo client
        groq = GroqClient()

        # Hiển thị info
        print("\n📊 Thông tin model:")
        info = groq.get_model_info()
        for key, value in info.items():
            print(f"  - {key}: {value}")

        # Test 1: Simple ask
        print("\n" + "=" * 70)
        print("TEST 1 - SIMPLE ASK")
        print("=" * 70)

        question = "Triệu chứng cảm cúm là gì? Trả lời ngắn gọn."
        print(f"\n❓ Câu hỏi: {question}")
        print(f"\n🤖 Trả lời:")

        answer = groq.simple_ask(question)
        print(answer)

        # Test 2: Chat với system prompt
        print("\n" + "=" * 70)
        print("TEST 2 - CHAT VỚI SYSTEM PROMPT")
        print("=" * 70)

        system_prompt = """Bạn là trợ lý y tế AI. 
Trả lời ngắn gọn, đúng trọng tâm. 
Không chẩn đoán bệnh hay kê đơn thuốc.
Luôn khuyến nghị đi khám bác sĩ nếu nghiêm trọng."""

        question = "Đau đầu kéo dài nên làm gì?"
        print(f"\n❓ Câu hỏi: {question}")
        print(f"\n🤖 Trả lời:")

        answer = groq.simple_ask(question, system_prompt)
        print(answer)

        # Test 3: Streaming
        print("\n" + "=" * 70)
        print("TEST 3 - STREAMING RESPONSE")
        print("=" * 70)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Cách phòng ngừa cảm cúm hiệu quả?"}
        ]

        print(f"\n❓ Câu hỏi: Cách phòng ngừa cảm cúm hiệu quả?")
        print(f"\n🤖 Trả lời (streaming):")

        for chunk in groq.chat_stream(messages):
            print(chunk, end='', flush=True)

        print("\n")

        # Test 4: Conversation với history
        print("\n" + "=" * 70)
        print("TEST 4 - CONVERSATION VỚI HISTORY")
        print("=" * 70)

        conversation = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Tôi bị sốt và đau đầu"},
            {"role": "assistant", "content": "Sốt và đau đầu có thể là dấu hiệu của cảm cúm. Bạn nên nghỉ ngơi, uống nhiều nước, và theo dõi nhiệt độ. Nếu sốt >38.5°C hoặc kéo dài >2 ngày, hãy đi khám bác sĩ."},
            {"role": "user", "content": "Tôi nên uống thuốc gì?"}
        ]

        print("\n💬 Hội thoại:")
        print("User: Tôi bị sốt và đau đầu")
        print("Bot: Sốt và đau đầu có thể là dấu hiệu của cảm cúm...")
        print("User: Tôi nên uống thuốc gì?")
        print("\n🤖 Bot:")

        response = groq.chat(conversation)
        print(response)

        print("\n✅ Demo hoàn tất!")

    except ValueError as e:
        print(f"\n{e}")
        print("\n📝 Hướng dẫn lấy Groq API Key:")
        print("1. Truy cập: https://console.groq.com")
        print("2. Đăng ký/Đăng nhập (miễn phí)")
        print("3. Vào 'API Keys' → Create API Key")
        print("4. Copy key và thêm vào config/.env:")
        print("   GROQ_API_KEY=gsk_xxxxxxxxxxxxxx")


if __name__ == "__main__":
    demo_groq_client()
