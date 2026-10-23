from __future__ import annotations

import os
from typing import Any

from openai import AsyncOpenAI


class UserMessage:
    def __init__(self, text: str | None = None, file_contents=None):
        self.text = text
        self.file_contents = list(file_contents or [])


class LlmChat:
    def __init__(
        self,
        api_key: str,
        session_id: str,
        system_message: str,
        *,
        initial_messages: list[dict[str, Any]] | None = None,
        custom_headers: dict[str, str] | None = None,
        base_url: str | None = None,
    ):
        self.session_id = session_id
        self.model = "gpt-4o-mini"
        self.params: dict[str, Any] = {}
        headers = dict(custom_headers or {})
        app_id = os.getenv("APP_URL") or os.getenv("REACT_APP_BACKEND_URL")
        if app_id:
            headers.setdefault("X-App-ID", app_id)
        proxy_url = os.getenv("INTEGRATION_PROXY_URL", "https://integrations.emergentagent.com")
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url or f"{proxy_url.rstrip('/')}/llm" if api_key.startswith("sk-emergent-") else base_url,
            default_headers=headers or None,
        )
        self.messages = list(initial_messages or [{"role": "system", "content": system_message}])

    def with_model(self, provider: str, model: str) -> "LlmChat":
        self.model = model
        return self

    def with_params(self, **params: Any) -> "LlmChat":
        self.params.update(params)
        return self

    async def send_message(self, user_message: UserMessage) -> str:
        if not user_message.text:
            raise ValueError("UserMessage.text is required")
        content: str | list[dict[str, Any]] = user_message.text
        if user_message.file_contents:
            content = [{"type": "text", "text": user_message.text}]
            for item in user_message.file_contents:
                if isinstance(item, str) and item.startswith("data:image/"):
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": item},
                    })
        self.messages.append({"role": "user", "content": content})
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            **self.params,
        )
        text = response.choices[0].message.content or ""
        self.messages.append({"role": "assistant", "content": text})
        return text