from __future__ import annotations

import os
import re

from .context_manager import RuntimeContext
from .llm import LLMService
from .models import Intent, IntentType, PendingFollowUp


APP_ALIASES = {
    "notepad": "notepad",
    "notes": "notepad",
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "edge",
    "calculator": "calculator",
    "calc": "calculator",
    "vscode": "vscode",
    "vs code": "vscode",
    "code": "vscode",
    "explorer": "explorer",
    "file explorer": "explorer",
}

FOLDER_ALIASES = {
    "downloads": "downloads",
    "download": "downloads",
    "desktop": "desktop",
    "documents": "documents",
    "pictures": "pictures",
    "music": "music",
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


class IntentParser:
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    def parse(self, text: str, context: RuntimeContext) -> Intent:
        normalized = normalize_text(text)

        mixed = self._detect_mixed(text)
        if mixed:
            return mixed

        if any(phrase in normalized for phrase in ("assistant stop", "stop assistant", "band ho ja", "shut down now")):
            return Intent(IntentType.STOP_ASSISTANT, raw_text=text, confidence=0.95)
        if any(phrase in normalized for phrase in ("pause assistant", "assistant pause", "thoda ruk ja")):
            return Intent(IntentType.PAUSE_ASSISTANT, raw_text=text, confidence=0.95)
        if any(phrase in normalized for phrase in ("resume assistant", "assistant resume", "wapas shuru ho ja")):
            return Intent(IntentType.RESUME_ASSISTANT, raw_text=text, confidence=0.95)

        if "screenshot" in normalized or "screenshot lo" in normalized:
            return Intent(IntentType.SCREENSHOT, raw_text=text, confidence=0.95)

        if "volume" in normalized or "awaz" in normalized:
            if any(word in normalized for word in ("kam", "down", "low", "decrease")):
                return Intent(IntentType.VOLUME, raw_text=text, confidence=0.9, value="down")
            if any(word in normalized for word in ("badha", "increase", "up", "high")):
                return Intent(IntentType.VOLUME, raw_text=text, confidence=0.9, value="up")
            return Intent(IntentType.VOLUME, raw_text=text, confidence=0.75, value="mute")

        if any(word in normalized for word in ("shutdown", "restart", "lock")):
            if "shutdown" in normalized:
                return Intent(IntentType.POWER, raw_text=text, confidence=0.95, value="shutdown")
            if "restart" in normalized:
                return Intent(IntentType.POWER, raw_text=text, confidence=0.95, value="restart")
            return Intent(IntentType.POWER, raw_text=text, confidence=0.95, value="lock")

        if any(phrase in normalized for phrase in ("generate image", "image generate", "image banao", "image create")):
            prompt = self._extract_image_prompt(normalized)
            if prompt:
                return Intent(IntentType.IMAGE_GENERATION, raw_text=text, confidence=0.9, value=prompt)
            return Intent(
                IntentType.IMAGE_GENERATION,
                raw_text=text,
                confidence=0.8,
                follow_up=PendingFollowUp(
                    kind="image_prompt",
                    question="Kis cheez ka image generate karun?",
                    intent_type=IntentType.IMAGE_GENERATION,
                ),
            )

        if "youtube" in normalized:
            query = self._extract_youtube_query(normalized)
            if query:
                return Intent(IntentType.YOUTUBE_PLAY, raw_text=text, confidence=0.92, value=query)
            if context.last_search_target and any(phrase in normalized for phrase in ("ab play karo", "play karo", "isko play karo")):
                return Intent(IntentType.YOUTUBE_PLAY, raw_text=text, confidence=0.78, value=context.last_search_target)
            return Intent(
                IntentType.YOUTUBE_PLAY,
                raw_text=text,
                confidence=0.72,
                follow_up=PendingFollowUp(
                    kind="youtube_query",
                    question="Kaunsa song ya video play karun?",
                    intent_type=IntentType.YOUTUBE_PLAY,
                ),
            )

        if "google" in normalized or "search" in normalized:
            query = self._extract_google_query(normalized)
            if query:
                return Intent(IntentType.GOOGLE_SEARCH, raw_text=text, confidence=0.9, value=query)
            if "ab search karo" in normalized and context.last_search_target:
                return Intent(IntentType.GOOGLE_SEARCH, raw_text=text, confidence=0.75, value=context.last_search_target)

        for folder_phrase, folder_name in FOLDER_ALIASES.items():
            if folder_phrase in normalized and any(word in normalized for word in ("open", "khol", "show")):
                return Intent(IntentType.OPEN_FOLDER, raw_text=text, confidence=0.9, target=folder_name)

        if "file kholo" in normalized or "folder kholo" in normalized:
            return Intent(
                IntentType.OPEN_FOLDER,
                raw_text=text,
                confidence=0.7,
                follow_up=PendingFollowUp(
                    kind="folder_target",
                    question="Kaunsa folder ya file open karna hai?",
                    intent_type=IntentType.OPEN_FOLDER,
                ),
            )

        app_target = self._extract_app_target(normalized)
        if app_target:
            if "close" in normalized or "band karo" in normalized:
                return Intent(IntentType.CLOSE_APP, raw_text=text, confidence=0.9, target=app_target)
            if app_target == "vscode" and any(phrase in normalized for phrase in ("folder open", "this folder", "ye folder", "is folder")):
                folder_target = os.getcwd() if any(phrase in normalized for phrase in ("this folder", "ye folder", "is folder")) else ""
                return Intent(IntentType.OPEN_IN_VSCODE, raw_text=text, confidence=0.9, target=folder_target or os.getcwd())
            follow_up = None
            if app_target == "notepad":
                follow_up = PendingFollowUp(
                    kind="notepad_typing",
                    question="Sir, kya type karun?",
                    intent_type=IntentType.TYPE_TEXT,
                    payload={"target_app": "notepad"},
                )
            return Intent(IntentType.OPEN_APP, raw_text=text, confidence=0.92, target=app_target, follow_up=follow_up)

        if any(phrase in normalized for phrase in ("type this", "yehi type karo", "message type karo", "type karo")):
            typed_value = self._extract_after_keywords(normalized, ["type this", "type karo", "message type karo", "yehi type karo"])
            if typed_value:
                return Intent(IntentType.TYPE_TEXT, raw_text=text, confidence=0.88, value=typed_value)
            return Intent(
                IntentType.TYPE_TEXT,
                raw_text=text,
                confidence=0.72,
                follow_up=PendingFollowUp(
                    kind="generic_typing",
                    question="Kya type karna hai?",
                    intent_type=IntentType.TYPE_TEXT,
                ),
            )

        if normalized.startswith("open ") and "." in normalized:
            return Intent(IntentType.OPEN_WEBSITE, raw_text=text, confidence=0.8, value=normalized.replace("open ", "", 1))

        llm_payload = self.llm_service.interpret_intent(text, context.conversation_context)
        if llm_payload:
            intent_name = llm_payload.get("intent", "unknown")
            mapped = IntentType(intent_name) if intent_name in IntentType._value2member_map_ else IntentType.UNKNOWN
            return Intent(
                mapped,
                raw_text=text,
                confidence=float(llm_payload.get("confidence", 0.5)),
                target=llm_payload.get("target"),
                value=llm_payload.get("value"),
                reply_hint=llm_payload.get("reply_hint"),
            )

        return Intent(IntentType.CHAT, raw_text=text, confidence=0.45)

    def fulfil_follow_up(self, text: str, context: RuntimeContext) -> Intent:
        pending = context.pending_follow_up
        normalized = normalize_text(text)
        if not pending:
            return self.parse(text, context)
        if pending.kind == "notepad_typing":
            return Intent(IntentType.TYPE_TEXT, raw_text=text, confidence=0.95, value=text, target=pending.payload.get("target_app"))
        if pending.kind == "youtube_query":
            return Intent(IntentType.YOUTUBE_PLAY, raw_text=text, confidence=0.95, value=text)
        if pending.kind == "image_prompt":
            return Intent(IntentType.IMAGE_GENERATION, raw_text=text, confidence=0.95, value=text)
        if pending.kind == "folder_target":
            return Intent(IntentType.OPEN_FOLDER, raw_text=text, confidence=0.9, target=FOLDER_ALIASES.get(normalized, text))
        if pending.kind == "generic_typing":
            return Intent(IntentType.TYPE_TEXT, raw_text=text, confidence=0.95, value=text)
        if pending.kind == "power_confirmation":
            if any(word in normalized for word in ("haan", "yes", "confirm", "kar do", "continue", "proceed")):
                return Intent(
                    IntentType.POWER,
                    raw_text=text,
                    confidence=0.95,
                    value=pending.payload.get("action", "shutdown"),
                    parameters={"confirmed": True},
                )
            return Intent(IntentType.CANCEL, raw_text=text, confidence=0.92, value=pending.payload.get("action", "power action"))
        return self.parse(text, context)

    def _extract_app_target(self, text: str) -> str | None:
        for alias, target in APP_ALIASES.items():
            if alias in text and any(trigger in text for trigger in ("open", "launch", "khol", "start", "close", "band")):
                return target
        return None

    def _extract_google_query(self, text: str) -> str | None:
        patterns = [
            r"google pe (?P<query>.+?) search karo",
            r"google pe (?P<query>.+)",
            r"search (?P<query>.+?) on google",
            r"search for (?P<query>.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group("query").strip()
        return None

    def _extract_youtube_query(self, text: str) -> str | None:
        patterns = [
            r"youtube pe (?P<query>.+?) (baja|play karo|chalao)",
            r"play (?P<query>.+?) on youtube",
            r"youtube pe (?P<query>.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                query = match.group("query").strip()
                if query and query not in {"gana", "song", "video"}:
                    return query
        return None

    def _extract_after_keywords(self, text: str, keywords: list[str]) -> str | None:
        for keyword in keywords:
            if keyword in text:
                tail = text.split(keyword, 1)[1].strip(" :,-")
                if tail:
                    return tail
        return None

    def _extract_image_prompt(self, text: str) -> str | None:
        patterns = [
            r"(?P<prompt>.+?) ka image generate karo",
            r"(?P<prompt>.+?) ka image banao",
            r"generate image (?P<prompt>.+)",
            r"image generate (?P<prompt>.+)",
            r"image banao (?P<prompt>.+)",
            r"image create karo (?P<prompt>.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                prompt = match.group("prompt").strip(" ,.-")
                if prompt:
                    return prompt
        return None

    def _detect_mixed(self, text: str) -> Intent | None:
        """
        Detect common mixed requests like "X aur google pe Y search karo" or
        "Binary search samjha aur notepad me notes likh do".
        """
        lowered = normalize_text(text)

        # Explain + Google search
        match = re.search(r"(.+?) aur google pe (.+?) search (karo|kar do)", lowered)
        if match:
            explain_part = match.group(1).strip()
            query_part = match.group(2).strip()
            return Intent(
                IntentType.GOOGLE_SEARCH,
                raw_text=text,
                confidence=0.9,
                value=query_part,
                parameters={"explain_first": explain_part},
            )

        # Explain + Notepad notes
        match = re.search(r"(.+?) aur (notepad|notes?) me (.+?) (likh|type) (do|kar do)?", lowered)
        if match:
            explain_part = match.group(1).strip()
            note_text = match.group(3).strip()
            return Intent(
                IntentType.TYPE_TEXT,
                raw_text=text,
                confidence=0.9,
                target="notepad",
                value=note_text,
                parameters={"explain_first": explain_part},
            )

        # Pure explain triggers go to chat; handled later
        return None
