from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jarvis_assistant.brain import AssistantBrain
from jarvis_assistant.config import IMAGE_DIR, load_settings
from jarvis_assistant.models import ActionResult


@dataclass
class Scenario:
    name: str
    command: str
    expected_intent: str
    expected_action: str
    expected_success: bool = True
    requires_follow_up: bool = False


class FakeAutomation:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def open_application(self, app_name: str) -> ActionResult:
        self.calls.append(("open_application", app_name))
        return ActionResult(
            True,
            f"{app_name} opened",
            "open_app",
            "open_application",
            steps=[f"mock open {app_name}"],
            target=app_name,
        )

    def close_application(self, app_name: str) -> ActionResult:
        self.calls.append(("close_application", app_name))
        return ActionResult(True, f"{app_name} closed", "close_app", "close_application", target=app_name)

    def open_folder(self, target: str) -> ActionResult:
        self.calls.append(("open_folder", target))
        return ActionResult(True, f"{target} opened", "open_folder", "open_folder", target=target)

    def open_in_vscode(self, folder: str) -> ActionResult:
        self.calls.append(("open_in_vscode", folder))
        return ActionResult(True, f"{folder} opened in vscode", "open_in_vscode", "open_in_vscode", target=folder)

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
        screenshot_path = str(Path("data") / "screenshots" / "mock.png")
        return ActionResult(True, screenshot_path, "screenshot", "take_screenshot", target=screenshot_path)

    def adjust_volume(self, direction: str) -> ActionResult:
        self.calls.append(("adjust_volume", direction))
        return ActionResult(True, f"volume {direction}", "volume", "adjust_volume", target=direction)

    def power_action(self, action: str) -> ActionResult:
        self.calls.append(("power_action", action))
        return ActionResult(True, f"power {action} blocked in test", "power", "power_action", target=action)


class FakeImageGeneration:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate(self, prompt: str) -> ActionResult:
        self.calls.append(prompt)
        image_path = str(IMAGE_DIR / "mock_generated.png")
        return ActionResult(
            True,
            f"image generated for {prompt}",
            "image_generation",
            "generate_image",
            target=image_path,
            payload={"path": image_path, "prompt": prompt},
        )


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


def build_brain() -> AssistantBrain:
    settings = load_settings()
    settings.startup_launch_voice = False
    settings.always_listen = False
    settings.permissions.power_actions = False
    brain = AssistantBrain(settings)
    fake_automation = FakeAutomation()
    fake_llm = FakeLLM()
    brain.automation = fake_automation
    brain.image_generation = FakeImageGeneration()
    brain.llm_service = fake_llm
    brain.parser.llm_service = fake_llm
    return brain


def run_suite(brain: AssistantBrain, iterations: int) -> list[str]:
    failures: list[str] = []
    scenarios = [
        Scenario("notepad_follow_up_start", "notepad kholo", "open_app", "open_application", requires_follow_up=True),
        Scenario("google_search", "google pe python automation search karo", "google_search", "google_search"),
        Scenario("youtube_play", "youtube pe believer song baja", "youtube_play", "youtube_play"),
        Scenario("screenshot", "screenshot lo", "screenshot", "take_screenshot"),
        Scenario("image_generation", "ek futuristic bike ka image generate karo", "image_generation", "generate_image"),
        Scenario("mixed_search", "python automation kya hota hai aur google pe python automation search karo", "google_search", "google_search"),
        Scenario("chat_only", "binary search kya hota hai", "chat", "chat_reply"),
    ]

    for iteration in range(iterations):
        brain.context_manager.set_follow_up(None)
        for scenario in scenarios:
            result = brain.handle_input(scenario.command, source="chat")
            if result.interpreted_intent != scenario.expected_intent:
                failures.append(
                    f"iteration {iteration + 1} {scenario.name}: expected intent {scenario.expected_intent}, got {result.interpreted_intent}"
                )
            if result.executed_action != scenario.expected_action:
                failures.append(
                    f"iteration {iteration + 1} {scenario.name}: expected action {scenario.expected_action}, got {result.executed_action}"
                )
            if result.success != scenario.expected_success:
                failures.append(
                    f"iteration {iteration + 1} {scenario.name}: expected success {scenario.expected_success}, got {result.success}"
                )
            if scenario.requires_follow_up and not result.requires_follow_up:
                failures.append(f"iteration {iteration + 1} {scenario.name}: expected follow-up to be required")

            if scenario.name == "notepad_follow_up_start":
                follow_up = brain.handle_input("smoke test typing", source="chat")
                if follow_up.interpreted_intent != "type_text" or follow_up.executed_action != "type_text":
                    failures.append(
                        f"iteration {iteration + 1} notepad_follow_up_finish: expected type_text/type_text, got {follow_up.interpreted_intent}/{follow_up.executed_action}"
                    )

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe automation stress test for the Jarvis assistant.")
    parser.add_argument("--iterations", type=int, default=5, help="Number of times to run the scenario suite.")
    args = parser.parse_args()

    brain = build_brain()
    failures = run_suite(brain, args.iterations)

    if failures:
        print("STRESS TEST FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"STRESS TEST PASSED ({args.iterations} iterations)")
    print("Checked: follow-up flow, system intents, mixed intents, image routing, chat routing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
