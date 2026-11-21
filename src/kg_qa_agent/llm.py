from __future__ import annotations

import requests

from .config import Settings, settings


class ChatClient:
    """Minimal client for OpenAI-compatible chat-completions endpoints."""

    def __init__(self, config: Settings = settings) -> None:
        config.require_llm()
        self.config = config

    def complete(self, messages: list[dict[str, str]], temperature: float = 0.0) -> str:
        response = requests.post(
            f"{self.config.llm_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.config.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.config.llm_model,
                "messages": messages,
                "temperature": temperature,
            },
            timeout=self.config.request_timeout,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]

