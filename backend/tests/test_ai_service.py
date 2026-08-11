import unittest
from unittest.mock import AsyncMock, patch

import httpx

from backend.services.ai_service import AIProviderError, AIService


class _AsyncClientContext:
    def __init__(self, response):
        self.post = AsyncMock(return_value=response)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None


class AIServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_provider_errors_are_not_reported_as_success(self):
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        response = httpx.Response(401, request=request, json={"error": "invalid key"})
        service = AIService(api_key="bad-key", base_url="https://api.openai.com/v1")

        with patch("backend.services.ai_service.httpx.AsyncClient", return_value=_AsyncClientContext(response)):
            with self.assertRaises(AIProviderError):
                await service.generate_response("User", "Giá bao nhiêu?")

    async def test_empty_completion_is_rejected(self):
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        response = httpx.Response(200, request=request, json={"choices": []})
        service = AIService(api_key="key", base_url="https://api.openai.com/v1")

        with patch("backend.services.ai_service.httpx.AsyncClient", return_value=_AsyncClientContext(response)):
            with self.assertRaises(AIProviderError):
                await service.generate_response("User", "Còn hàng không?")
