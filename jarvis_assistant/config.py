from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
SCREENSHOT_DIR = DATA_DIR / "screenshots"
IMAGE_DIR = DATA_DIR / "generated_images"
SETTINGS_PATH = DATA_DIR / "settings.json"
DB_PATH = DATA_DIR / "jarvis.db"
LOG_PATH = LOG_DIR / "jarvis.log"


def ensure_directories() -> None:
    for path in (DATA_DIR, LOG_DIR, SCREENSHOT_DIR, IMAGE_DIR):
        path.mkdir(parents=True, exist_ok=True)


@dataclass
class PermissionSettings:
    app_control: bool = True
    browser_control: bool = True
    mouse_control: bool = True
    keyboard_typing: bool = True
    clipboard_access: bool = True
    screenshot_access: bool = True
    power_actions: bool = False
    dangerous_action_confirmation: bool = True


@dataclass
class AppSettings:
    assistant_name: str = "Jarvis"
    wake_phrase: str = "hey jarvis"
    reply_style: str = "professional"
    theme: str = "light"
    preferred_browser: str = "default"
    startup_launch_voice: bool = False
    minimize_to_tray: bool = True
    always_listen: bool = False
    microphone_name: str = ""
    speaker_name: str = ""
    ai_model: str = "gpt-4.1-mini"
    image_model: str = "gpt-image-1"
    openai_api_key: str = ""
    openai_base_url: str = ""
    default_search_engine: str = "google"
    permissions: PermissionSettings = field(default_factory=PermissionSettings)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "AppSettings":
        permissions = PermissionSettings(**payload.get("permissions", {}))
        data = dict(payload)
        data["permissions"] = permissions
        return cls(**data)


def load_settings() -> AppSettings:
    load_dotenv(PROJECT_ROOT / ".env")
    ensure_directories()
    if SETTINGS_PATH.exists():
        payload = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        settings = AppSettings.from_dict(payload)
    else:
        settings = AppSettings()
        save_settings(settings)

    if not settings.openai_api_key:
        settings.openai_api_key = os.getenv("OPENAI_API_KEY", "")
    if not settings.openai_base_url:
        settings.openai_base_url = os.getenv("OPENAI_BASE_URL", "")
    return settings


def save_settings(settings: AppSettings) -> None:
    ensure_directories()
    SETTINGS_PATH.write_text(json.dumps(settings.to_dict(), indent=2), encoding="utf-8")
