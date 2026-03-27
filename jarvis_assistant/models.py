from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AssistantStatus(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    PAUSED = "paused"
    STOPPED = "stopped"


class IntentType(str, Enum):
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    OPEN_FOLDER = "open_folder"
    GOOGLE_SEARCH = "google_search"
    YOUTUBE_PLAY = "youtube_play"
    TYPE_TEXT = "type_text"
    SCREENSHOT = "screenshot"
    VOLUME = "volume"
    POWER = "power"
    OPEN_WEBSITE = "open_website"
    OPEN_IN_VSCODE = "open_in_vscode"
    SWITCH_WINDOW = "switch_window"
    CHAT = "chat"
    IMAGE_GENERATION = "image_generation"
    PAUSE_ASSISTANT = "pause_assistant"
    RESUME_ASSISTANT = "resume_assistant"
    STOP_ASSISTANT = "stop_assistant"
    UNKNOWN = "unknown"


@dataclass
class PendingFollowUp:
    kind: str
    question: str
    intent_type: IntentType
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Intent:
    intent_type: IntentType
    raw_text: str
    confidence: float = 0.0
    target: str | None = None
    value: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    follow_up: PendingFollowUp | None = None
    reply_hint: str | None = None


@dataclass
class ActionResult:
    success: bool
    reply: str
    interpreted_intent: str
    executed_action: str
    steps: list[str] = field(default_factory=list)
    target: str | None = None
    error: str | None = None
    requires_follow_up: bool = False
    follow_up_question: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class CommandRecord:
    raw_command: str
    interpreted_intent: str
    target: str | None
    executed_steps: list[str]
    success: bool
    follow_up_kind: str | None
    error: str | None
    created_at: datetime = field(default_factory=datetime.utcnow)
