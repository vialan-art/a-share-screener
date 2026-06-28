"""AI 顾问接口。

兼容 OpenAI 格式：
- URL
- API Key
- model
- temperature
- thinking_effort（由模型返回，程序透传）
"""
import json
from typing import List, Dict, Any, AsyncGenerator
import httpx
from backend.core.config import get_settings


settings = get_settings()


class AIAdvisor:
    """AI 顾问。"""

    SYSTEM_PROMPT = """你是一位耐心的价值投资助教，用户是投资初学者。
请用简单、清晰的中文解释投资概念和分析结果。
回答时要区分事实和推断，不要给出具体的买卖建议。
如果有不确定的地方，请明确说明。"""

    def __init__(self):
        self.enabled = settings.ai_advisor_enabled
        self.api_url = settings.ai_advisor_api_url
        self.api_key = settings.ai_advisor_api_key
        self.model = settings.ai_advisor_model
        self.temperature = settings.ai_advisor_temperature

    async def chat(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """非流式对话。"""
        if not self.enabled:
            return {
                "content": "AI 顾问未启用。请在 .env 中设置 AI_ADVISOR_ENABLED=true 和 API Key。",
                "model": self.model,
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": self.SYSTEM_PROMPT}] + messages,
            "temperature": self.temperature,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        # 透传 thinking_effort（如果模型返回的话）
        extra = {}
        if "thinking_effort" in data:
            extra["thinking_effort"] = data["thinking_effort"]

        return {
            "content": content,
            "model": data.get("model", self.model),
            **extra,
        }

    async def chat_stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """流式对话（SSE 格式）。"""
        if not self.enabled:
            yield "AI 顾问未启用。请在 .env 中设置 AI_ADVISOR_ENABLED=true 和 API Key。"
            return

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": self.SYSTEM_PROMPT}] + messages,
            "temperature": self.temperature,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", self.api_url, headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0]["delta"]
                        if "content" in delta and delta["content"]:
                            yield delta["content"]
                    except (json.JSONDecodeError, KeyError):
                        continue
