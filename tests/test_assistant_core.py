from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jarvis_assistant.brain import AssistantBrain
from jarvis_assistant.config import AppSettings
from jarvis_assistant.models import ActionResult
from jarvis_assistant.context_manager import ContextManager
from jarvis_assistant.automation import WindowsAutomation


@dataclass
class FakeAutomation:
    calls: list[tuple[str, str]]

    def open_application(self, app_name: str) -> ActionResult:
        self.calls.append(("open_application", app_name))
        return ActionResult(True, f"{app_name} opened", "open_app", "open_application", target=app_name)

    def close_application(self, app_name: str) -> ActionResult:
        self.calls.append(("close_application", app_name))
        return ActionResult(True, f"{app_name} closed", "close_app", "close_application", target=app_name)

    def open_folder(self, target: str) -> ActionResult:
        self.calls.append(("open_folder", target))
        return ActionResult(True, f"{target} opened", "open_folder", "open_folder", target=target)

    def open_in_vscode(self, folder: str) -> ActionResult:
        self.calls.append(("open_in_vscode", folder))
        return ActionResult(True, f"{folder} opened", "open_in_vscode", "open_in_vscode", target=folder)

    def open_website(self, url: str) -> ActionResult:
        self.calls.append(("open_website", url))
        return ActionResult(True, f"{url} opened", "open_website", "open_website", target=url)

    def google_search(self, query: str) -> ActionResult:
        self.calls.append(("google_search", query))
        return ActionResult(True, f"searched {query}", "google_search", "google_search", target=query)

    def youtube_play(self, query: str) -> ActionResult:
        self.calls.append(("youtube_play", query))
        return ActionResult(True, f"playing {query}", "youtube_play", "youtube_play", target=query)

    def type_text(self, text: str) -> ActionResult:
        self.calls.append(("type_text", text))
        return ActionResult(True, f"typed {text}", "type_text", "type_text", target=text)

    def switch_to_last_window(self) -> ActionResult:
        self.calls.append(("switch_to_last_window", ""))
        return ActionResult(True, "switched", "switch_window", "switch_window")

    def take_screenshot(self) -> ActionResult:
        self.calls.append(("take_screenshot", ""))
        return ActionResult(True, "shot", "screenshot", "take_screenshot", target="shot")

    def adjust_volume(self, direction: str) -> ActionResult:
        self.calls.append(("adjust_volume", direction))
        return ActionResult(True, f"volume {direction}", "volume", "adjust_volume", target=direction)

    def power_action(self, action: str) -> ActionResult:
        self.calls.append(("power_action", action))
        return ActionResult(True, f"power {action}", "power", "power_action", target=action)


class FakeImageGeneration:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate(self, prompt: str) -> ActionResult:
        self.calls.append(prompt)
        return ActionResult(True, f"generated {prompt}", "image_generation", "generate_image", target=prompt)


class FakeLLM:
    def __init__(self) -> None:
        self.chat_calls: list[str] = []
        self._configured = True
        self._last_error: str | None = None

    def is_configured(self) -> bool:
        return self._configured

    def interpret_intent(self, text: str, context: list[str]) -> dict | None:
        return None

    def chat_reply(self, text: str, context: list[str], assistant_name: str) -> str:
        self.chat_calls.append(text)
        self._last_error = None
        return f"[mock-chat] {text}"

    def last_error(self) -> str | None:
        return self._last_error


class AssistantCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        settings = AppSettings()
        settings.startup_launch_voice = False
        settings.openai_api_key = ""
        self.brain = AssistantBrain(settings)
        self.brain.history_store.record = lambda record: None  # type: ignore[assignment]
        self.fake_automation = FakeAutomation(calls=[])
        self.fake_llm = FakeLLM()
        self.fake_image = FakeImageGeneration()
        self.brain.automation = self.fake_automation
        self.brain.image_generation = self.fake_image
        self.brain.llm_service = self.fake_llm
        self.brain.parser.llm_service = self.fake_llm

    def test_default_openai_base_url_is_set(self) -> None:
        self.assertEqual(AppSettings().openai_base_url, "https://api.openai.com/v1")

    def test_notepad_requires_follow_up(self) -> None:
        result = self.brain.handle_input("notepad kholo", source="chat")
        self.assertTrue(result.requires_follow_up)
        self.assertEqual(result.interpreted_intent, "open_app")
        self.assertEqual(result.executed_action, "open_application")

    def test_notepad_follow_up_types_text(self) -> None:
        self.brain.handle_input("notepad kholo", source="chat")
        result = self.brain.handle_input("hello notes", source="chat")
        self.assertEqual(result.interpreted_intent, "type_text")
        self.assertEqual(result.executed_action, "type_text")
        self.assertIn(("type_text", "hello notes"), self.fake_automation.calls)

    def test_google_search_intent_executes(self) -> None:
        result = self.brain.handle_input("google pe python automation search karo", source="chat")
        self.assertEqual(result.interpreted_intent, "google_search")
        self.assertEqual(result.executed_action, "google_search")

    def test_mixed_request_answers_and_searches(self) -> None:
        result = self.brain.handle_input("python automation kya hota hai aur google pe python automation search karo", source="chat")
        self.assertEqual(result.interpreted_intent, "google_search")
        self.assertEqual(result.executed_action, "google_search")
        self.assertIn("[mock-chat]", result.reply)

    def test_image_generation_route_executes(self) -> None:
        result = self.brain.handle_input("ek futuristic bike ka image generate karo", source="chat")
        self.assertEqual(result.interpreted_intent, "image_generation")
        self.assertEqual(result.executed_action, "generate_image")
        self.assertEqual(self.fake_image.calls, ["ek futuristic bike"])

    def test_chat_question_routes_to_chat_reply(self) -> None:
        result = self.brain.handle_input("binary search kya hota hai", source="chat")
        self.assertEqual(result.interpreted_intent, "chat")
        self.assertEqual(result.executed_action, "chat_reply")

    def test_chat_without_llm_configuration_returns_clear_error(self) -> None:
        self.fake_llm._configured = False
        result = self.brain.handle_input("binary search kya hota hai", source="chat")
        self.assertEqual(result.interpreted_intent, "chat")
        self.assertEqual(result.executed_action, "chat_unavailable")
        self.assertFalse(result.success)

    def test_power_action_requires_confirmation_follow_up(self) -> None:
        self.brain.settings.permissions.power_actions = True
        result = self.brain.handle_input("system shutdown karo", source="chat")
        self.assertTrue(result.requires_follow_up)
        self.assertEqual(result.executed_action, "request_follow_up")
        confirm = self.brain.handle_input("haan", source="chat")
        self.assertEqual(confirm.interpreted_intent, "power")
        self.assertEqual(confirm.executed_action, "power_action")
        self.assertIn(("power_action", "shutdown"), self.fake_automation.calls)

    def test_browser_permission_gate_blocks_google_search(self) -> None:
        settings = AppSettings()
        settings.permissions.browser_control = False
        automation = WindowsAutomation(settings, ContextManager())
        result = automation.google_search("python automation")
        self.assertFalse(result.success)
        self.assertEqual(result.interpreted_intent, "permission_denied")

    def test_google_search_requires_typing_permission(self) -> None:
        settings = AppSettings()
        settings.permissions.keyboard_typing = False
        automation = WindowsAutomation(settings, ContextManager())
        result = automation.google_search("python automation")
        self.assertFalse(result.success)
        self.assertEqual(result.interpreted_intent, "permission_denied")


if __name__ == "__main__":
    unittest.main()
