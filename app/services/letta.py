from __future__ import annotations

import asyncio
from typing import Any

from app.settings import Settings

try:
    from letta_client import Letta
except ImportError:  # pragma: no cover - optional dependency
    Letta = None


class LettaLearningClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: Any | None = None
        self._enabled = bool(
            settings.letta_learning_enabled
            and settings.letta_agent_id
            and (settings.letta_api_key or settings.letta_base_url)
            and Letta is not None
        )

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if Letta is None:
            raise RuntimeError("letta-client is not installed.")
        client_kwargs: dict[str, Any] = {}
        if self.settings.letta_api_key:
            client_kwargs["api_key"] = self.settings.letta_api_key
        if self.settings.letta_base_url:
            client_kwargs["base_url"] = self.settings.letta_base_url
        self._client = Letta(**client_kwargs)
        return self._client

    async def store_validation_lesson(self, lesson_text: str) -> str | None:
        if not self.enabled:
            return None
        print("[learning][letta] storing validation lesson")
        prompt = (
            "Store the following validated flood-prediction lesson in memory. "
            "Update your internal memory with recurring bias, calibration advice, and horizon-specific guidance. "
            "Reply with a one-line acknowledgement only.\n\n"
            f"{lesson_text}"
        )
        return await asyncio.to_thread(self._send_message, prompt)

    async def fetch_learning_summary(self) -> str | None:
        if not self.enabled:
            return None
        print("[learning][letta] requesting learning summary")
        prompt = (
            "Return a compact summary of your current learning for Hong Kong flood prediction at the configured horizon. "
            "Include recent bias direction, approximate hit rate, and up to 3 adjustment rules. "
            "Keep the answer under 120 words."
        )
        return await asyncio.to_thread(self._send_message, prompt)

    def _send_message(self, content: str) -> str | None:
        client = self._get_client()
        response = client.agents.messages.create(
            agent_id=self.settings.letta_agent_id,
            messages=[{"role": "user", "content": content}],
        )
        return self._extract_assistant_text(response)

    def _extract_assistant_text(self, response: Any) -> str | None:
        messages = getattr(response, "messages", None)
        if messages is None and isinstance(response, dict):
            messages = response.get("messages")
        if not messages:
            return None
        for message in reversed(list(messages)):
            message_type = getattr(message, "message_type", None)
            if message_type is None and isinstance(message, dict):
                message_type = message.get("message_type")
            if message_type != "assistant_message":
                continue
            content = getattr(message, "content", None)
            if content is None and isinstance(message, dict):
                content = message.get("content")
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                parts: list[str] = []
                for item in content:
                    if isinstance(item, str):
                        parts.append(item)
                    elif isinstance(item, dict) and "text" in item:
                        parts.append(str(item["text"]))
                joined = " ".join(part.strip() for part in parts if part).strip()
                if joined:
                    return joined
        return None
