from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

try:
    import pyttsx3
except ImportError:  # pragma: no cover
    pyttsx3 = None

try:
    import speech_recognition as sr
except ImportError:  # pragma: no cover
    sr = None

from .config import AppSettings
from .models import AssistantStatus


class VoicePipeline:
    def __init__(self, settings: AppSettings, status_callback: Callable[[AssistantStatus], None] | None = None) -> None:
        self.settings = settings
        self.status_callback = status_callback
        self.logger = logging.getLogger(__name__)
        self._listener_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._engine = self._build_engine()

    def _build_engine(self):
        if not pyttsx3:
            return None
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 175)
            return engine
        except Exception as exc:  # pragma: no cover
            self.logger.warning("TTS engine unavailable: %s", exc)
            return None

    def speak(self, text: str) -> None:
        if self.status_callback:
            self.status_callback(AssistantStatus.SPEAKING)
        if self._engine:
            self._engine.say(text)
            self._engine.runAndWait()
        self.logger.info("Assistant reply: %s", text)
        if self.status_callback:
            self.status_callback(AssistantStatus.IDLE)

    def listen_once(self, timeout: int = 5, phrase_time_limit: int = 8) -> str | None:
        if not sr:
            return None
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                if self.status_callback:
                    self.status_callback(AssistantStatus.LISTENING)
                recognizer.pause_threshold = 0.8
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                return recognizer.recognize_google(audio, language="en-IN").strip()
        except sr.WaitTimeoutError:
            return None
        except Exception as exc:
            self.logger.warning("Voice listen failed: %s", exc)
            return None
        finally:
            if self.status_callback:
                self.status_callback(AssistantStatus.IDLE)

    def start_background_listening(self, on_text: Callable[[str], None]) -> None:
        if self._listener_thread and self._listener_thread.is_alive():
            return
        self._stop_event.clear()

        def runner() -> None:
            while not self._stop_event.is_set():
                heard = self.listen_once()
                if not heard:
                    continue
                command = heard
                if self.settings.wake_phrase and not self.settings.always_listen:
                    lowered = heard.lower()
                    wake = self.settings.wake_phrase.lower()
                    if wake not in lowered:
                        time.sleep(0.2)
                        continue
                    command = lowered.split(wake, 1)[1].strip(" ,")
                    if not command:
                        continue
                on_text(command)
                time.sleep(0.2)

        self._listener_thread = threading.Thread(target=runner, daemon=True)
        self._listener_thread.start()

    def stop_background_listening(self) -> None:
        self._stop_event.set()
