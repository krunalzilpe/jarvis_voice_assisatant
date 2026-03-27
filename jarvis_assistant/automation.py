from __future__ import annotations

import ctypes
import logging
import os
import subprocess
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

try:
    import pyautogui
except ImportError:  # pragma: no cover
    pyautogui = None

try:
    import pygetwindow as gw
except ImportError:  # pragma: no cover
    gw = None

try:
    import pyperclip
except ImportError:  # pragma: no cover
    pyperclip = None

try:
    from yt_dlp import YoutubeDL
except ImportError:  # pragma: no cover
    YoutubeDL = None

from .config import AppSettings, IMAGE_DIR, SCREENSHOT_DIR
from .context_manager import ContextManager
from .models import ActionResult


class WindowsAutomation:
    def __init__(self, settings: AppSettings, context_manager: ContextManager) -> None:
        self.settings = settings
        self.context_manager = context_manager
        self.logger = logging.getLogger(__name__)

    def open_application(self, app_name: str) -> ActionResult:
        if not self.settings.permissions.app_control:
            return self._denied("App control permission is disabled.")
        mapping = {
            "notepad": ["notepad.exe"],
            "calculator": ["calc.exe"],
            "chrome": ["chrome.exe"],
            "edge": ["msedge.exe"],
            "explorer": ["explorer.exe"],
            "vscode": ["code"],
        }
        command = mapping.get(app_name)
        if not command:
            return ActionResult(False, f"{app_name} ke liye launcher configured nahi hai.", "open_app", "open_application", target=app_name)
        try:
            subprocess.Popen(command)
            time.sleep(1.2)
            self.focus_window(app_name)
            self.context_manager.set_active(app=app_name, window=app_name.title())
            return ActionResult(True, f"{app_name.title()} khol diya.", "open_app", "open_application", steps=[f"Started {app_name} via {' '.join(command)}."], target=app_name)
        except Exception as exc:
            return ActionResult(False, f"{app_name.title()} open nahi ho paya.", "open_app", "open_application", error=str(exc), target=app_name)

    def close_application(self, app_name: str) -> ActionResult:
        if not self.settings.permissions.app_control:
            return self._denied("App control permission is disabled.")
        process_map = {
            "notepad": "notepad.exe",
            "calculator": "CalculatorApp.exe",
            "chrome": "chrome.exe",
            "edge": "msedge.exe",
            "explorer": "explorer.exe",
            "vscode": "Code.exe",
        }
        try:
            subprocess.run(["taskkill", "/IM", process_map.get(app_name, app_name), "/F"], capture_output=True, text=True, check=False)
            return ActionResult(True, f"{app_name.title()} band kar diya.", "close_app", "close_application", steps=[f"Requested process kill for {app_name}."], target=app_name)
        except Exception as exc:
            return ActionResult(False, f"{app_name.title()} band nahi ho paya.", "close_app", "close_application", error=str(exc), target=app_name)

    def open_folder(self, target: str) -> ActionResult:
        if not self.settings.permissions.app_control:
            return self._denied("App control permission is disabled.")
        folders = {
            "downloads": Path.home() / "Downloads",
            "desktop": Path.home() / "Desktop",
            "documents": Path.home() / "Documents",
            "pictures": Path.home() / "Pictures",
            "music": Path.home() / "Music",
        }
        path = folders.get(target.lower(), Path(target).expanduser())
        if not path.exists():
            return ActionResult(False, f"Path nahi mila: {path}", "open_folder", "open_folder", target=str(path))
        os.startfile(path)  # type: ignore[attr-defined]
        self.context_manager.set_active(app="explorer", window=str(path))
        return ActionResult(True, f"{path} open kar diya.", "open_folder", "open_folder", steps=[f"Opened {path} in Explorer."], target=str(path))

    def open_in_vscode(self, folder: str) -> ActionResult:
        if not self.settings.permissions.app_control:
            return self._denied("App control permission is disabled.")
        resolved = str(Path(folder).expanduser())
        try:
            subprocess.Popen(["code", resolved])
            self.context_manager.set_active(app="vscode", window=resolved)
            return ActionResult(True, f"VS Code mein {resolved} open kar diya.", "open_in_vscode", "open_in_vscode", steps=[f"Executed code {resolved}."], target=resolved)
        except Exception as exc:
            return ActionResult(False, "VS Code open nahi ho paya.", "open_in_vscode", "open_in_vscode", error=str(exc), target=resolved)

    def open_website(self, url: str) -> ActionResult:
        if not self.settings.permissions.browser_control:
            return self._denied("Browser control permission is disabled.")
        target = url if url.startswith("http") else f"https://{url}"
        webbrowser.open(target)
        self.context_manager.set_active(app=self.settings.preferred_browser or "browser", window=target)
        return ActionResult(True, f"Website open kar di: {target}", "open_website", "open_website", steps=[f"Opened URL {target}."], target=target)

    def google_search(self, query: str) -> ActionResult:
        if not self.settings.permissions.browser_control:
            return self._denied("Browser control permission is disabled.")
        url = "https://www.google.com"
        webbrowser.open(url)
        steps = ["Opened browser.", "Navigated to Google."]
        time.sleep(3)
        if pyautogui:
            pyautogui.write(query, interval=0.02)
            pyautogui.press("enter")
            steps.append("Typed the query into the Google search box and submitted it.")
        else:
            webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
            steps.append("Fell back to opening the Google results URL directly.")
        self.context_manager.set_last_search_target(query)
        self.context_manager.set_active(app=self.settings.preferred_browser or "browser", window="Google Search")
        return ActionResult(True, f"Google pe {query} search kar diya.", "google_search", "google_search", steps=steps, target=query)

    def youtube_play(self, query: str) -> ActionResult:
        if not self.settings.permissions.browser_control:
            return self._denied("Browser control permission is disabled.")
        target_url = "https://www.youtube.com"
        webbrowser.open(target_url)
        steps = ["Opened browser.", "Opened YouTube."]
        time.sleep(4)
        if pyautogui:
            pyautogui.hotkey("ctrl", "l")
            pyautogui.write(target_url, interval=0.01)
            pyautogui.press("enter")
            time.sleep(4)
            pyautogui.press("/")
            time.sleep(0.4)
            pyautogui.write(query, interval=0.02)
            pyautogui.press("enter")
            steps.append("Focused the YouTube search box, typed the query, and submitted it.")
            time.sleep(4)
        resolved_url = None
        if YoutubeDL:
            try:
                with YoutubeDL({"quiet": True, "extract_flat": True, "skip_download": True}) as ydl:
                    info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                    entries = info.get("entries", [])
                    if entries and entries[0].get("id"):
                        resolved_url = f"https://www.youtube.com/watch?v={entries[0]['id']}"
                        steps.append("Resolved the top YouTube result with yt-dlp.")
            except Exception as exc:
                self.logger.warning("yt-dlp lookup failed: %s", exc)
        if resolved_url:
            webbrowser.open(resolved_url)
            steps.append("Opened the top-matching YouTube result directly.")
            time.sleep(4)
        elif pyautogui:
            pyautogui.press("tab")
            pyautogui.press("tab")
            pyautogui.press("enter")
            steps.append("Used keyboard navigation to open the first visible YouTube result.")
            time.sleep(4)
        if pyautogui:
            pyautogui.press("k")
            steps.append("Sent play shortcut to ensure playback starts.")
        self.context_manager.set_last_search_target(query)
        self.context_manager.set_active(app=self.settings.preferred_browser or "browser", window="YouTube")
        return ActionResult(True, f"YouTube pe {query} play kar diya.", "youtube_play", "youtube_play", steps=steps, target=query)

    def type_text(self, text: str) -> ActionResult:
        if not self.settings.permissions.keyboard_typing:
            return self._denied("Keyboard typing permission is disabled.")
        if not pyautogui:
            return ActionResult(False, "Typing automation ke liye pyautogui install hona chahiye.", "type_text", "type_text")
        steps = []
        if self.context_manager.state.last_opened_app:
            self.focus_window(self.context_manager.state.last_opened_app)
            time.sleep(0.6)
            steps.append(f"Focused {self.context_manager.state.last_opened_app} before typing.")
        if pyperclip and self.settings.permissions.clipboard_access:
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            steps.append("Pasted text through clipboard.")
        else:
            pyautogui.write(text, interval=0.02)
            steps.append("Typed text character by character.")
        return ActionResult(True, "Text type kar diya.", "type_text", "type_text", steps=steps, target=self.context_manager.state.active_app or "active_window")

    def focus_window(self, name: str) -> bool:
        if not gw:
            return False
        candidates = {
            "notepad": ["Notepad"],
            "chrome": ["Chrome"],
            "edge": ["Microsoft Edge", "Edge"],
            "vscode": ["Visual Studio Code", "Code"],
            "explorer": ["File Explorer", "Downloads", "Documents", "Desktop"],
            "calculator": ["Calculator"],
        }.get(name.lower(), [name])
        for window in gw.getAllWindows():
            title = window.title or ""
            if any(candidate.lower() in title.lower() for candidate in candidates):
                try:
                    window.activate()
                    self.context_manager.set_active(app=name, window=title)
                    return True
                except Exception:
                    continue
        return False

    def switch_to_last_window(self) -> ActionResult:
        if gw:
            title = self.context_manager.state.active_window
            matches = [window for window in gw.getAllWindows() if title.lower() in window.title.lower()]
            if matches:
                matches[0].activate()
                return ActionResult(True, f"{title} focus kar diya.", "switch_window", "switch_window", steps=[f"Activated window {title}."], target=title)
        if pyautogui:
            pyautogui.hotkey("alt", "tab")
            return ActionResult(True, "Last window focus kar diya.", "switch_window", "switch_window", steps=["Sent Alt+Tab."])
        return ActionResult(False, "Window switch nahi ho paya.", "switch_window", "switch_window")

    def take_screenshot(self) -> ActionResult:
        if not self.settings.permissions.screenshot_access:
            return self._denied("Screenshot permission is disabled.")
        if not pyautogui:
            return ActionResult(False, "Screenshot ke liye pyautogui install hona chahiye.", "screenshot", "take_screenshot")
        filename = SCREENSHOT_DIR / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        image = pyautogui.screenshot()
        image.save(filename)
        return ActionResult(True, f"Screenshot save kar diya: {filename}", "screenshot", "take_screenshot", steps=[f"Captured current screen to {filename}."], target=str(filename))

    def adjust_volume(self, direction: str) -> ActionResult:
        if not pyautogui:
            return ActionResult(False, "Volume automation ke liye pyautogui install hona chahiye.", "volume", "adjust_volume")
        key = {"up": "volumeup", "down": "volumedown", "mute": "volumemute"}.get(direction, "volumemute")
        presses = 5 if direction in {"up", "down"} else 1
        for _ in range(presses):
            pyautogui.press(key)
        return ActionResult(True, f"Volume {direction} kar diya.", "volume", "adjust_volume", steps=[f"Pressed {key} {presses} times."], target=direction)

    def power_action(self, action: str) -> ActionResult:
        if not self.settings.permissions.power_actions:
            return self._denied("Power actions permission is disabled.")
        if self.settings.permissions.dangerous_action_confirmation:
            return ActionResult(True, f"{action} blocked hai jab tak dangerous action confirmation disable ya explicit confirm na ho.", "power", "power_action", steps=["Confirmation gate prevented the power action."], target=action)
        if action == "lock":
            ctypes.windll.user32.LockWorkStation()
            return ActionResult(True, "System lock kar diya.", "power", "power_action", steps=["Locked workstation."], target=action)
        commands = {
            "shutdown": ["shutdown", "/s", "/t", "5"],
            "restart": ["shutdown", "/r", "/t", "5"],
        }
        try:
            subprocess.Popen(commands[action])
            return ActionResult(True, f"System {action} command run kar diya.", "power", "power_action", steps=[f"Executed {action} command."], target=action)
        except Exception as exc:
            return ActionResult(False, f"{action} execute nahi ho paya.", "power", "power_action", error=str(exc), target=action)

    def save_generated_image(self, image_bytes: bytes, filename: str) -> str:
        path = IMAGE_DIR / filename
        path.write_bytes(image_bytes)
        return str(path)

    def _denied(self, message: str) -> ActionResult:
        return ActionResult(False, message, "permission_denied", "permission_check", error=message)
