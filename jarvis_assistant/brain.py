from __future__ import annotations

import logging
from collections.abc import Callable

from .automation import WindowsAutomation
from .config import AppSettings, DB_PATH
from .context_manager import ContextManager
from .image_generation import ImageGenerationService
from .llm import LLMService
from .models import ActionResult, AssistantStatus, IntentType
from .nlu import IntentParser
from .storage import HistoryStore
from .voice import VoicePipeline


class AssistantBrain:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.context_manager = ContextManager()
        self.logger = logging.getLogger(__name__)
        self.history_store = HistoryStore(DB_PATH)
        self.llm_service = LLMService(settings)
        self.parser = IntentParser(self.llm_service)
        self.automation = WindowsAutomation(settings, self.context_manager)
        self.voice = VoicePipeline(settings, self.context_manager.update_status)
        self.image_generation = ImageGenerationService(settings, self.automation)
        self._listeners: list[Callable[[ActionResult], None]] = []

    def add_listener(self, listener: Callable[[ActionResult], None]) -> None:
        self._listeners.append(listener)

    def start(self) -> None:
        self.context_manager.update_status(AssistantStatus.IDLE)
        if self.settings.startup_launch_voice:
            self.start_background_agent()

    def start_background_agent(self) -> None:
        self.voice.start_background_listening(lambda text: self.handle_input(text, source="voice"))
        self.context_manager.set_background_running(True)

    def stop_background_agent(self) -> None:
        self.voice.stop_background_listening()
        self.context_manager.set_background_running(False)

    def speak(self, text: str) -> None:
        self.voice.speak(text)
        self.context_manager.remember_reply(text)

    def handle_input(self, text: str, source: str = "chat") -> ActionResult:
        self.context_manager.update_status(AssistantStatus.PROCESSING)
        self.context_manager.remember_command(text)
        runtime = self.context_manager.state
        intent = self.parser.fulfil_follow_up(text, runtime) if runtime.pending_follow_up else self.parser.parse(text, runtime)
        if runtime.pending_follow_up:
            self.context_manager.set_follow_up(None)
        result = self._execute_intent(intent)
        self.context_manager.set_last_action(result.executed_action)
        self.context_manager.remember_reply(result.reply)
        self.context_manager.update_status(AssistantStatus.IDLE if result.interpreted_intent != IntentType.PAUSE_ASSISTANT.value else AssistantStatus.PAUSED)
        self.history_store.record(self.history_store.summarize_result(text, result))
        for listener in self._listeners:
            listener(result)
        if source == "voice":
            self.speak(result.reply)
        return result

    def _execute_intent(self, intent) -> ActionResult:
        if intent.follow_up:
            self.context_manager.set_follow_up(intent.follow_up)

        match intent.intent_type:
            case IntentType.OPEN_APP:
                result = self.automation.open_application(intent.target or "")
                if result.success and intent.follow_up:
                    result.requires_follow_up = True
                    result.follow_up_question = intent.follow_up.question
                    result.reply = f"{result.reply} {intent.follow_up.question}"
                return result
            case IntentType.CLOSE_APP:
                return self.automation.close_application(intent.target or "")
            case IntentType.OPEN_FOLDER:
                if intent.follow_up:
                    return ActionResult(True, intent.follow_up.question, intent.intent_type.value, "request_follow_up", requires_follow_up=True, follow_up_question=intent.follow_up.question)
                return self.automation.open_folder(intent.target or "")
            case IntentType.OPEN_IN_VSCODE:
                return self.automation.open_in_vscode(intent.target or "")
            case IntentType.GOOGLE_SEARCH:
                reply_prefix = None
                if intent.parameters.get("explain_first"):
                    reply_prefix = self.llm_service.chat_reply(intent.parameters["explain_first"], self.context_manager.state.conversation_context, self.settings.assistant_name)
                action_result = self.automation.google_search(intent.value or "")
                if reply_prefix:
                    action_result.reply = f"{reply_prefix}\n\n{action_result.reply}"
                return action_result
            case IntentType.YOUTUBE_PLAY:
                if intent.follow_up:
                    return ActionResult(True, intent.follow_up.question, intent.intent_type.value, "request_follow_up", requires_follow_up=True, follow_up_question=intent.follow_up.question)
                return self.automation.youtube_play(intent.value or "")
            case IntentType.TYPE_TEXT:
                if intent.follow_up:
                    return ActionResult(True, intent.follow_up.question, intent.intent_type.value, "request_follow_up", requires_follow_up=True, follow_up_question=intent.follow_up.question)
                if intent.target == "notepad" and self.context_manager.state.last_opened_app != "notepad":
                    self.automation.open_application("notepad")
                reply_prefix = None
                if intent.parameters.get("explain_first"):
                    reply_prefix = self.llm_service.chat_reply(intent.parameters["explain_first"], self.context_manager.state.conversation_context, self.settings.assistant_name)
                action_result = self.automation.type_text(intent.value or "")
                if reply_prefix:
                    action_result.reply = f"{reply_prefix}\n\n{action_result.reply}"
                return action_result
            case IntentType.SCREENSHOT:
                return self.automation.take_screenshot()
            case IntentType.VOLUME:
                return self.automation.adjust_volume(intent.value or "mute")
            case IntentType.POWER:
                return self.automation.power_action(intent.value or "shutdown")
            case IntentType.OPEN_WEBSITE:
                return self.automation.open_website(intent.value or "")
            case IntentType.SWITCH_WINDOW:
                return self.automation.switch_to_last_window()
            case IntentType.IMAGE_GENERATION:
                if intent.follow_up:
                    return ActionResult(True, intent.follow_up.question, intent.intent_type.value, "request_follow_up", requires_follow_up=True, follow_up_question=intent.follow_up.question)
                return self.image_generation.generate(intent.value or "")
            case IntentType.PAUSE_ASSISTANT:
                self.stop_background_agent()
                return ActionResult(True, "Assistant pause kar diya.", intent.intent_type.value, "pause_assistant")
            case IntentType.RESUME_ASSISTANT:
                self.start_background_agent()
                return ActionResult(True, "Assistant resume kar diya.", intent.intent_type.value, "resume_assistant")
            case IntentType.STOP_ASSISTANT:
                self.stop_background_agent()
                return ActionResult(True, "Assistant stop kar diya.", intent.intent_type.value, "stop_assistant")
            case IntentType.CHAT:
                reply = self.llm_service.chat_reply(intent.raw_text, self.context_manager.state.conversation_context, self.settings.assistant_name)
                if reply:
                    return ActionResult(True, reply, intent.intent_type.value, "chat_reply")
                return ActionResult(True, "Command samajh gaya, lekin uske liye specific action configure nahi hai. Aap aur specific bol sakte hain.", intent.intent_type.value, "chat_fallback")
            case _:
                return ActionResult(False, "Ye command abhi samajh nahi aaya.", IntentType.UNKNOWN.value, "unknown")
