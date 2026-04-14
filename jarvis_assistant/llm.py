from __future__ import annotations

import json
import logging

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from .config import AppSettings


class LLMService:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self._last_error: str | None = None

    def is_configured(self) -> bool:
        return bool(self.settings.openai_api_key and OpenAI)

    def _client(self) -> OpenAI:
        kwargs = {"api_key": self.settings.openai_api_key}
        if self.settings.openai_base_url:
            kwargs["base_url"] = self.settings.openai_base_url
        return OpenAI(**kwargs)

    def interpret_intent(self, text: str, context: list[str]) -> dict | None:
        if not self.is_configured():
            self._last_error = "OpenAI client is not configured."
            return None
        prompt = (
            "Return compact JSON with keys intent, target, value, confidence, reply_hint. "
            "Intents: open_app, close_app, open_folder, google_search, youtube_play, "
            "type_text, screenshot, volume, power, image_generation, chat, unknown."
        )
        try:
            response = self._client().responses.create(
                model=self.settings.ai_model,
                input=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps({"context": context[-6:], "command": text})},
                ],
            )
            content = getattr(response, "output_text", "").strip()
            self._last_error = None
            return json.loads(content) if content else None
        except Exception as exc:  # pragma: no cover
            self._last_error = self._format_exception(exc)
            self.logger.warning("LLM intent interpretation failed: %s", self._last_error)
            return None

    def chat_reply(self, text: str, context: list[str], assistant_name: str) -> str | None:
        if not self.is_configured():
            self._last_error = "OpenAI client is not configured."
            return None
        try:
            response = self._client().responses.create(
                model=self.settings.ai_model,
                input=[
                    {
                        "role": "system",
                        "content": f"You are {assistant_name}, a concise Windows assistant that helps complete tasks.",
                    },
                    {"role": "user", "content": json.dumps({"context": context[-10:], "message": text})},
                ],
            )
            self._last_error = None
            return getattr(response, "output_text", "").strip() or None
        except Exception as exc:  # pragma: no cover
            self._last_error = self._format_exception(exc)
            self.logger.warning("LLM chat reply failed: %s", self._last_error)
            return None

    def last_error(self) -> str | None:
        return self._last_error

    def _format_exception(self, exc: Exception) -> str:
        message = str(exc).strip()
        if message:
            return message
        return exc.__class__.__name__
