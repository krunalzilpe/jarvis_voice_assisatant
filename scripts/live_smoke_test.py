from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jarvis_assistant.brain import AssistantBrain
from jarvis_assistant.config import load_settings


def run_live(include_youtube: bool = False) -> int:
    settings = load_settings()
    settings.permissions.power_actions = False
    brain = AssistantBrain(settings)

    scenarios = [
        "notepad kholo",
        "live smoke test from assistant",
        "google pe python automation search karo",
        "screenshot lo",
    ]
    if include_youtube:
        scenarios.insert(3, "youtube pe believer song baja")

    print("LIVE SMOKE TEST START")
    for command in scenarios:
        print(f">>> {command}")
        result = brain.handle_input(command, source="chat")
        print(f"success={result.success} intent={result.interpreted_intent} action={result.executed_action}")
        print(result.reply)
        if not result.success:
            print("LIVE SMOKE TEST FAILED")
            return 1
        time.sleep(3)

    print("LIVE SMOKE TEST PASSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Runs real desktop smoke automation against the assistant.")
    parser.add_argument("--youtube", action="store_true", help="Include YouTube playback test.")
    args = parser.parse_args()
    return run_live(include_youtube=args.youtube)


if __name__ == "__main__":
    raise SystemExit(main())
