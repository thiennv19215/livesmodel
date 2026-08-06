import re
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "Bạn là MC livestream bán hàng chuyên nghiệp, hào hứng và duyên dáng. "
    "Nhiệm vụ: Trả lời ngắn gọn từ 1-2 câu (khoảng 45 từ, tối đa 220 ký tự), "
    "thân thiện, chào khán giả bằng tên và chốt đơn tự nhiên nếu có sản phẩm."
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

    def sanitize_reply(self, reply: str) -> str:
        """Enforces hard maximum ceiling of 220 characters and 1-2 sentences."""
        reply = re.sub(r'\s+', ' ', reply).strip()
        if len(reply) > 220:
            # Truncate to nearest complete sentence or 217 chars + ...
            sentences = re.split(r'(?<=[.!?])\s+', reply)
            trimmed = ""
            for s in sentences:
                if len(trimmed + " " + s) <= 220:
                    trimmed += (" " if trimmed else "") + s
                else:
                    break
            reply = trimmed if trimmed else reply[:217] + "..."
        return reply

    def get_event_template_reply(self, event_type: str, user_name: str) -> str:
        """Template replies for non-chat interaction events (gift, follow, share)."""
        event_labels = {
            "gift": "tặng quà cho phòng live",
            "follow": "theo dõi kênh",
            "share": "chia sẻ phiên livestream"
        }
        action_label = event_labels.get(event_type, "tương tác")
        return f"Cảm ơn bạn {user_name} đã {action_label}, chúc bạn một ngày tốt lành và mua sắm vui vẻ nha!"

    async def generate_response(self, user_name: str, user_comment: str, product_context: Optional[str] = None, event_type: str = "chat") -> str:
        if event_type in ["gift", "follow", "share"]:
            return self.get_event_template_reply(event_type, user_name)

        prompt_content = f"Khán giả '{user_name}' bình luận: '{user_comment}'."
        if product_context:
            prompt_content += f"\nThông tin sản phẩm phù hợp: {product_context}."

        if not self.api_key and self.provider in ["openai", "openrouter"]:
            # Fallback mock response when API key is not configured
            if product_context:
                res = f"Dạ chào {user_name}, sản phẩm này đang sale cực hời luôn nha! Bạn bấm ngay vào giỏ hàng góc trái màn hình để nhận ưu đãi nha!"
            else:
                res = f"Cảm ơn {user_name} đã thả cmt nha! Bạn thả tim và theo dõi kênh để nhận thêm deal hời nhé!"
            return self.sanitize_reply(res)

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
                    reply = data.get("message", {}).get("content", "").strip()
                    return self.sanitize_reply(reply)

            else:  # OpenAI / OpenRouter / DeepSeek
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
                            "max_tokens": 120,
                            "temperature": 0.7
                        }
                    )
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        reply = choices[0]["message"]["content"].strip()
                        return self.sanitize_reply(reply)
                    return f"Cảm ơn {user_name} đã tương tác livestream nha!"

        except Exception as e:
            logger.error(f"Error calling LLM provider {self.provider}: {e}")
            return self.sanitize_reply(f"Dạ chào {user_name}, cảm ơn bạn đã quan tâm livestream nha!")
