from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .models import AssistantStatus, PendingFollowUp


@dataclass
class RuntimeContext:
    status: AssistantStatus = AssistantStatus.IDLE
    last_command: str = ""
    last_action: str = ""
    active_window: str = ""
    active_app: str = ""
    last_opened_app: str = ""
    last_search_target: str = ""
    pending_follow_up: PendingFollowUp | None = None
    conversation_context: list[str] = field(default_factory=list)
    background_agent_running: bool = False
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ContextManager:
    def __init__(self) -> None:
        self.state = RuntimeContext()

    def update_status(self, status: AssistantStatus) -> None:
        self.state.status = status
        self.state.last_updated = datetime.now(timezone.utc)

    def remember_command(self, text: str) -> None:
        self.state.last_command = text
        self.state.conversation_context.append(f"user: {text}")
        self.state.conversation_context = self.state.conversation_context[-20:]
        self.state.last_updated = datetime.now(timezone.utc)

    def remember_reply(self, text: str) -> None:
        self.state.conversation_context.append(f"assistant: {text}")
        self.state.conversation_context = self.state.conversation_context[-20:]
        self.state.last_updated = datetime.now(timezone.utc)

    def set_active(self, app: str = "", window: str = "") -> None:
        if app:
            self.state.active_app = app
            self.state.last_opened_app = app
        if window:
            self.state.active_window = window
        self.state.last_updated = datetime.now(timezone.utc)

    def set_last_action(self, action: str) -> None:
        self.state.last_action = action
        self.state.last_updated = datetime.now(timezone.utc)

    def set_last_search_target(self, target: str) -> None:
        self.state.last_search_target = target
        self.state.last_updated = datetime.now(timezone.utc)

    def set_follow_up(self, pending: PendingFollowUp | None) -> None:
        self.state.pending_follow_up = pending
        self.state.last_updated = datetime.now(timezone.utc)

    def set_background_running(self, running: bool) -> None:
        self.state.background_agent_running = running
        self.state.last_updated = datetime.now(timezone.utc)
