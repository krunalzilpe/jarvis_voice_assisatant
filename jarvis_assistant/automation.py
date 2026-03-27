from __future__ import annotations

import ctypes
import logging
import os
import subprocess
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, urlparse

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
    from pywinauto import Desktop
except ImportError:  # pragma: no cover
    Desktop = None

try:
    from pywinauto.keyboard import send_keys
except ImportError:  # pragma: no cover
    send_keys = None

try:
    from yt_dlp import YoutubeDL
except ImportError:  # pragma: no cover
    YoutubeDL = None

from .config import AppSettings, IMAGE_DIR, SCREENSHOT_DIR
from .context_manager import ContextManager
from .models import ActionResult


APP_LAUNCHERS = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "chrome": ["chrome.exe"],
    "edge": ["msedge.exe"],
    "explorer": ["explorer.exe"],
    "vscode": ["code"],
}

PROCESS_NAMES = {
    "notepad": "notepad.exe",
    "calculator": "CalculatorApp.exe",
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
    "explorer": "explorer.exe",
    "vscode": "Code.exe",
}

WINDOW_CANDIDATES = {
    "notepad": ["Notepad"],
    "chrome": ["Chrome"],
    "edge": ["Microsoft Edge", "Edge"],
    "vscode": ["Visual Studio Code", "Code"],
    "explorer": ["File Explorer", "Downloads", "Documents", "Desktop"],
    "calculator": ["Calculator"],
}

BROWSER_WINDOW_KEYWORDS = ["Chrome", "Edge", "Firefox", "Brave", "Opera", "Google", "YouTube"]


class WindowsAutomation:
    def __init__(self, settings: AppSettings, context_manager: ContextManager) -> None:
        self.settings = settings
        self.context_manager = context_manager
        self.logger = logging.getLogger(__name__)
        if pyautogui:  # pragma: no branch
            pyautogui.PAUSE = 0.08

    def open_application(self, app_name: str) -> ActionResult:
        if not self.settings.permissions.app_control:
            return self._denied("App control permission is disabled.")
        command = APP_LAUNCHERS.get(app_name)
        if not command:
            return ActionResult(False, f"{app_name} ke liye launcher configured nahi hai.", "open_app", "open_application", target=app_name)
        steps = [f"Started {app_name} via {' '.join(command)}."]
        try:
            subprocess.Popen(command)
            title = self._wait_for_window(app_name, timeout=8)
            if title:
                steps.append(f"Verified application window: {title}.")
                self.context_manager.set_active(app=app_name, window=title)
            else:
                steps.append("Window verification timed out; continuing after launch request.")
                self.context_manager.set_active(app=app_name, window=app_name.title())
            return ActionResult(True, f"{app_name.title()} khol diya.", "open_app", "open_application", steps=steps, target=app_name)
        except Exception as exc:
            return self._failure(
                f"{app_name.title()} open nahi ho paya.",
                "open_app",
                "open_application",
                steps,
                app_name,
                exc,
            )

    def close_application(self, app_name: str) -> ActionResult:
        if not self.settings.permissions.app_control:
            return self._denied("App control permission is disabled.")
        try:
            subprocess.run(["taskkill", "/IM", PROCESS_NAMES.get(app_name, app_name), "/F"], capture_output=True, text=True, check=False)
            return ActionResult(True, f"{app_name.title()} band kar diya.", "close_app", "close_application", steps=[f"Requested process kill for {app_name}."], target=app_name)
        except Exception as exc:
            return self._failure(
                f"{app_name.title()} band nahi ho paya.",
                "close_app",
                "close_application",
                [f"Attempted to stop process for {app_name}."],
                app_name,
                exc,
            )

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
            title = self._wait_for_window("vscode", timeout=8)
            self.context_manager.set_active(app="vscode", window=title or resolved)
            steps = [f"Executed code {resolved}."]
            if title:
                steps.append(f"Verified VS Code window: {title}.")
            return ActionResult(True, f"VS Code mein {resolved} open kar diya.", "open_in_vscode", "open_in_vscode", steps=steps, target=resolved)
        except Exception as exc:
            return self._failure("VS Code open nahi ho paya.", "open_in_vscode", "open_in_vscode", [f"Attempted code {resolved}."], resolved, exc)

    def open_website(self, url: str) -> ActionResult:
        if not self.settings.permissions.browser_control:
            return self._denied("Browser control permission is disabled.")
        target = url if url.startswith("http") else f"https://{url}"
        steps: list[str] = []
        if not self._navigate_browser_to(target, steps, expected_fragments=[self._host_fragment(target)]):
            return ActionResult(False, f"Website open nahi ho payi: {target}", "open_website", "open_website", steps=steps, target=target)
        self.context_manager.set_active(app=self._browser_identity(), window=target)
        return ActionResult(True, f"Website open kar di: {target}", "open_website", "open_website", steps=steps, target=target)

    def google_search(self, query: str) -> ActionResult:
        if not self.settings.permissions.browser_control:
            return self._denied("Browser control permission is disabled.")
        if not self.settings.permissions.keyboard_typing:
            return self._denied("Browser search ke liye keyboard typing permission enable honi chahiye.")
        steps: list[str] = []
        google_url = "https://www.google.com"
        if not self._navigate_browser_to(google_url, steps, expected_fragments=["google.com"]):
            return ActionResult(False, "Google open nahi ho paya.", "google_search", "google_search", steps=steps, target=query)

        if not self._enter_text(
            query,
            steps,
            description="Typed the query into the Google search box and submitted it.",
            submit=True,
            prefer_clipboard=False,
        ):
            return ActionResult(False, "Google search query type nahi ho payi.", "google_search", "google_search", steps=steps, target=query)

        verified = self._wait_for_browser_url_contains(["google.com/search"], timeout=10)
        if verified:
            steps.append(f"Verified Google results page: {verified}.")
        else:
            recovery = f"https://www.google.com/search?q={quote_plus(query)}"
            webbrowser.open(recovery)
            steps.append("Typed search was not verified; opened the Google results URL as recovery.")
            recovered = self._wait_for_browser_url_contains(["google.com/search"], timeout=8)
            if recovered:
                steps.append(f"Verified recovery URL: {recovered}.")

        self.context_manager.set_last_search_target(query)
        self.context_manager.set_active(app=self._browser_identity(), window="Google Search")
        return ActionResult(True, f"Google pe {query} search kar diya.", "google_search", "google_search", steps=steps, target=query)

    def youtube_play(self, query: str) -> ActionResult:
        if not self.settings.permissions.browser_control:
            return self._denied("Browser control permission is disabled.")
        if not self.settings.permissions.keyboard_typing:
            return self._denied("YouTube automation ke liye keyboard typing permission enable honi chahiye.")
        steps: list[str] = []
        youtube_url = "https://www.youtube.com"
        if not self._navigate_browser_to(youtube_url, steps, expected_fragments=["youtube.com"]):
            return ActionResult(False, "YouTube open nahi ho paya.", "youtube_play", "youtube_play", steps=steps, target=query)

        if not self._send_shortcut(("shift", "/")):
            return ActionResult(False, "YouTube search box focus nahi ho paya.", "youtube_play", "youtube_play", steps=steps, target=query)
        steps.append("Focused the YouTube search box with the '/' shortcut.")
        time.sleep(0.3)
        if not self._enter_text(
            query,
            steps,
            description="Typed the query into the YouTube search box and submitted it.",
            submit=True,
            prefer_clipboard=False,
        ):
            return ActionResult(False, "YouTube query type nahi ho payi.", "youtube_play", "youtube_play", steps=steps, target=query)

        search_verified = self._wait_for_browser_url_contains(["youtube.com/results"], timeout=10)
        if search_verified:
            steps.append(f"Verified YouTube results page: {search_verified}.")

        resolved_url = self._resolve_youtube_result(query, steps)
        if resolved_url:
            if not self._navigate_browser_to(resolved_url, steps, expected_fragments=["youtube.com/watch"]):
                return ActionResult(False, "YouTube result open nahi ho paya.", "youtube_play", "youtube_play", steps=steps, target=query)
            steps.append("Opened the best matching YouTube result.")
        else:
            self._send_key("tab")
            self._send_key("tab")
            self._send_key("enter")
            steps.append("Used keyboard navigation to open the first visible YouTube result.")
            watch_verified = self._wait_for_browser_url_contains(["youtube.com/watch"], timeout=10)
            if watch_verified:
                steps.append(f"Verified YouTube watch page: {watch_verified}.")

        if self._send_key("k"):
            steps.append("Sent play shortcut to ensure playback starts.")

        self.context_manager.set_last_search_target(query)
        self.context_manager.set_active(app=self._browser_identity(), window="YouTube")
        return ActionResult(True, f"YouTube pe {query} play kar diya.", "youtube_play", "youtube_play", steps=steps, target=query)

    def type_text(self, text: str) -> ActionResult:
        if not self.settings.permissions.keyboard_typing:
            return self._denied("Keyboard typing permission is disabled.")
        steps: list[str] = []
        target_app = self.context_manager.state.last_opened_app or self.context_manager.state.active_app

        focused = False
        if target_app == "notepad":
            focused = self._focus_notepad_window(steps)
        elif target_app:
            focused = self.focus_window(target_app)
            if focused:
                steps.append(f"Focused {target_app} before typing.")

        if target_app and not focused:
            steps.append(f"Could not verify focus for {target_app}; typing into the current foreground window.")

        if not self._enter_text(text, steps, description="Entered the requested text into the active window.", submit=False, prefer_clipboard=True):
            return ActionResult(False, "Text type nahi ho paya.", "type_text", "type_text", steps=steps, target=target_app or "active_window")

        return ActionResult(True, "Text type kar diya.", "type_text", "type_text", steps=steps, target=target_app or "active_window")

    def focus_window(self, name: str) -> bool:
        title = self._activate_window(name, WINDOW_CANDIDATES.get(name.lower(), [name]))
        if not title:
            return False
        self.context_manager.set_active(app=name, window=title)
        return True

    def switch_to_last_window(self) -> ActionResult:
        title = self.context_manager.state.active_window
        if title:
            activated = self._activate_window(self.context_manager.state.active_app or title, [title])
            if activated:
                return ActionResult(True, f"{activated} focus kar diya.", "switch_window", "switch_window", steps=[f"Activated window {activated}."], target=activated)
        if self._send_shortcut(("alt", "tab")):
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
        if not self._typing_backend_available():
            return ActionResult(False, "Volume automation ke liye keyboard automation backend chahiye.", "volume", "adjust_volume")
        key = {"up": "volumeup", "down": "volumedown", "mute": "volumemute"}.get(direction, "volumemute")
        presses = 5 if direction in {"up", "down"} else 1
        for _ in range(presses):
            self._send_key(key)
        return ActionResult(True, f"Volume {direction} kar diya.", "volume", "adjust_volume", steps=[f"Pressed {key} {presses} times."], target=direction)

    def power_action(self, action: str) -> ActionResult:
        if not self.settings.permissions.power_actions:
            return self._denied("Power actions permission is disabled.")
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
            return self._failure(f"{action} execute nahi ho paya.", "power", "power_action", [f"Attempted {action} system command."], action, exc)

    def save_generated_image(self, image_bytes: bytes, filename: str) -> str:
        path = IMAGE_DIR / filename
        path.write_bytes(image_bytes)
        return str(path)

    def _navigate_browser_to(self, url: str, steps: list[str], expected_fragments: list[str] | None = None) -> bool:
        webbrowser.open(url)
        steps.append(f"Requested browser launch for {url}.")
        time.sleep(1.5)
        title = self._wait_for_browser_window(timeout=8)
        if title:
            steps.append(f"Focused browser window: {title}.")
        else:
            steps.append("Browser window could not be verified; continuing with direct navigation.")
        if self._typing_backend_available():
            self._send_shortcut(("ctrl", "l"))
            time.sleep(0.2)
            entered = self._enter_text(url, steps, description="Entered the target URL in the browser address bar and submitted it.", submit=True, prefer_clipboard=False)
            if not entered:
                return False
            fragments = expected_fragments or [self._host_fragment(url)]
            verified = self._wait_for_browser_url_contains(fragments, timeout=12)
            if verified:
                steps.append(f"Verified browser navigation: {verified}.")
                return True
            steps.append("Browser URL verification timed out.")
            return False
        return True

    def _resolve_youtube_result(self, query: str, steps: list[str]) -> str | None:
        if not YoutubeDL:
            return None
        try:
            with YoutubeDL({"quiet": True, "extract_flat": True, "skip_download": True}) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                entries = info.get("entries", [])
                if entries and entries[0].get("id"):
                    resolved = f"https://www.youtube.com/watch?v={entries[0]['id']}"
                    steps.append("Resolved the top YouTube result with yt-dlp.")
                    return resolved
        except Exception as exc:  # pragma: no cover
            self.logger.warning("yt-dlp lookup failed: %s", exc)
        return None

    def _enter_text(
        self,
        text: str,
        steps: list[str],
        description: str,
        *,
        submit: bool,
        prefer_clipboard: bool,
    ) -> bool:
        if pyautogui:
            if prefer_clipboard and pyperclip and self.settings.permissions.clipboard_access:
                previous_clipboard = self._safe_clipboard_read()
                try:
                    pyperclip.copy(text)
                    pyautogui.hotkey("ctrl", "v")
                finally:
                    if previous_clipboard is not None:
                        pyperclip.copy(previous_clipboard)
                steps.append(description.replace("Typed", "Pasted").replace("Entered", "Pasted"))
            else:
                pyautogui.write(text, interval=0.02)
                steps.append(description)
            if submit:
                pyautogui.press("enter")
            return True

        if send_keys:
            try:
                if prefer_clipboard and pyperclip and self.settings.permissions.clipboard_access:
                    previous_clipboard = self._safe_clipboard_read()
                    try:
                        pyperclip.copy(text)
                        send_keys("^v")
                    finally:
                        if previous_clipboard is not None:
                            pyperclip.copy(previous_clipboard)
                    steps.append(description.replace("Typed", "Pasted").replace("Entered", "Pasted"))
                else:
                    send_keys(text, with_spaces=True, pause=0.02)
                    steps.append(description)
                if submit:
                    send_keys("{ENTER}")
                return True
            except Exception as exc:  # pragma: no cover
                self.logger.warning("send_keys failed: %s", exc)
        return False

    def _send_shortcut(self, keys: tuple[str, ...]) -> bool:
        if pyautogui:
            pyautogui.hotkey(*keys)
            return True
        if send_keys and len(keys) == 2:
            translation = {
                ("ctrl", "l"): "^l",
                ("ctrl", "c"): "^c",
                ("ctrl", "v"): "^v",
                ("alt", "tab"): "%{TAB}",
                ("shift", "/"): "+/",
            }.get(keys)
            if translation:
                send_keys(translation)
                return True
        return False

    def _send_key(self, key: str) -> bool:
        if pyautogui:
            pyautogui.press(key)
            return True
        if send_keys:
            mapping = {
                "enter": "{ENTER}",
                "tab": "{TAB}",
                "k": "k",
                "volumeup": "{VOLUME_UP}",
                "volumedown": "{VOLUME_DOWN}",
                "volumemute": "{VOLUME_MUTE}",
            }.get(key, key)
            send_keys(mapping)
            return True
        return False

    def _wait_for_window(self, app_name: str, timeout: float = 8.0) -> str | None:
        end = time.time() + timeout
        while time.time() < end:
            title = self._activate_window(app_name, WINDOW_CANDIDATES.get(app_name.lower(), [app_name]))
            if title:
                return title
            time.sleep(0.5)
        return None

    def _wait_for_browser_window(self, timeout: float = 8.0) -> str | None:
        end = time.time() + timeout
        while time.time() < end:
            title = self._activate_window(self._browser_identity(), BROWSER_WINDOW_KEYWORDS)
            if title:
                return title
            time.sleep(0.5)
        return None

    def _activate_window(self, app_name: str, candidates: list[str]) -> str | None:
        if gw:
            for window in gw.getAllWindows():
                title = (window.title or "").strip()
                if title and any(candidate.lower() in title.lower() for candidate in candidates):
                    try:
                        window.activate()
                        self.context_manager.set_active(app=app_name, window=title)
                        return title
                    except Exception:
                        continue
        if Desktop:
            try:
                windows = Desktop(backend="uia").windows()
            except Exception:
                windows = []
            for window in windows:
                try:
                    title = (window.window_text() or "").strip()
                except Exception:
                    continue
                if title and any(candidate.lower() in title.lower() for candidate in candidates):
                    try:
                        window.set_focus()
                        self.context_manager.set_active(app=app_name, window=title)
                        return title
                    except Exception:
                        continue
        return None

    def _focus_notepad_window(self, steps: list[str]) -> bool:
        title = self._activate_window("notepad", WINDOW_CANDIDATES["notepad"])
        if title:
            steps.append(f"Focused Notepad window: {title}.")
            return True
        return False

    def _wait_for_browser_url_contains(self, fragments: list[str], timeout: float = 10.0) -> str | None:
        end = time.time() + timeout
        lowered_fragments = [fragment.lower() for fragment in fragments if fragment]
        while time.time() < end:
            current = self._read_browser_url()
            if current and all(fragment in current.lower() for fragment in lowered_fragments):
                return current
            time.sleep(0.6)
        return None

    def _read_browser_url(self) -> str | None:
        if not pyautogui or not pyperclip or not self.settings.permissions.clipboard_access:
            return None
        previous_clipboard = self._safe_clipboard_read()
        try:
            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.15)
            current = pyperclip.paste()
            pyautogui.press("esc")
            return str(current).strip() if current else None
        except Exception as exc:  # pragma: no cover
            self.logger.debug("Browser URL read failed: %s", exc)
            return None
        finally:
            if previous_clipboard is not None:
                try:
                    pyperclip.copy(previous_clipboard)
                except Exception:
                    pass

    def _safe_clipboard_read(self) -> str | None:
        if not pyperclip or not self.settings.permissions.clipboard_access:
            return None
        try:
            current = pyperclip.paste()
        except Exception:
            return None
        return str(current) if current is not None else None

    def _typing_backend_available(self) -> bool:
        return bool(pyautogui or send_keys)

    def _browser_identity(self) -> str:
        return self.settings.preferred_browser if self.settings.preferred_browser and self.settings.preferred_browser != "default" else "browser"

    def _host_fragment(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc or url

    def _failure(
        self,
        reply: str,
        interpreted_intent: str,
        executed_action: str,
        steps: list[str],
        target: str | None,
        exc: Exception,
    ) -> ActionResult:
        detail = str(exc).strip() or exc.__class__.__name__
        snapshot = self._capture_debug_snapshot(executed_action)
        if snapshot:
            steps.append(f"Saved failure snapshot: {snapshot}.")
        return ActionResult(False, reply, interpreted_intent, executed_action, steps=steps, target=target, error=detail, payload={"snapshot": snapshot} if snapshot else {})

    def _capture_debug_snapshot(self, label: str) -> str | None:
        if not pyautogui or not self.settings.permissions.screenshot_access:
            return None
        filename = SCREENSHOT_DIR / f"debug_{label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        try:
            pyautogui.screenshot().save(filename)
        except Exception:  # pragma: no cover
            return None
        return str(filename)

    def _denied(self, message: str) -> ActionResult:
        return ActionResult(False, message, "permission_denied", "permission_check", error=message)
