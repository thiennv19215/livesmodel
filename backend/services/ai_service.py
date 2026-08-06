import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "Bạn là MC livestream chuyên nghiệp, thân thiện và duyên dáng. "
    "Nhiệm vụ của bạn là trả lời bình luận của khán giả một cách ngắn gọn (tối đa 2-3 câu), "
    "hào hứng, giữ chân người xem và chốt đơn sản phẩm nếu có."
)

class AIService:
    def __init__(self, provider: str = "openai", api_key: str = "", base_url: str = "", model: str = ""):
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self.model = model or "gpt-4o-mini"
        self.system_prompt = DEFAULT_SYSTEM_PROMPT

    def set_system_prompt(self, prompt: str):
        if prompt.strip():
            self.system_prompt = prompt

    async def generate_response(self, user_name: str, user_comment: str, product_context: Optional[str] = None) -> str:
        prompt_content = f"Khán giả '{user_name}' hỏi: '{user_comment}'."
        if product_context:
            prompt_content += f"\nThông tin sản phẩm đang nhắc đến: {product_context}."

        if not self.api_key and self.provider == "openai":
            # Fallback mock response for testing when API key is not yet set
            if product_context:
                return f"Dạ chào bạn {user_name}, sản phẩm này siêu hot luôn nè! {product_context[:60]}... Bạn bấm ngay vào giỏ hàng góc trái nha!"
            return f"Cảm ơn bạn {user_name} đã bình luận nha! Bạn nhớ theo dõi kênh để không bỏ lỡ deal hời nhé!"

        try:
            if self.provider == "ollama":
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        f"{self.base_url}/api/chat",
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": self.system_prompt},
                                {"role": "user", "content": prompt_content}
                            ],
                            "stream": False
                        }
                    )
                    data = resp.json()
                    return data.get("message", {}).get("content", "").strip()

            else:  # OpenAI / OpenRouter / Compatible
                headers = {"Authorization": f"Bearer {self.api_key}"}
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": self.system_prompt},
                                {"role": "user", "content": prompt_content}
                            ],
                            "max_tokens": 150,
                            "temperature": 0.7
                        }
                    )
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0]["message"]["content"].strip()
                    return f"Cảm ơn bạn {user_name} đã bình luận!"

        except Exception as e:
            logger.error(f"Error calling LLM provider {self.provider}: {e}")
            return f"Dạ chào {user_name}, cảm ơn bạn đã quan tâm livestream nha!"
