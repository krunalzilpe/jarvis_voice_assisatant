from __future__ import annotations

import logging
import sys
import threading
import time
from collections.abc import Callable

try:
    import pyttsx3
except ImportError:  # pragma: no cover
    pyttsx3 = None

try:  # pragma: no cover
    import sounddevice as sd
except ImportError:  # pragma: no cover
    sd = None

try:  # pragma: no cover
    import numpy as np  # noqa: F401
except ImportError:  # pragma: no cover
    np = None

try:  # pragma: no cover
    import distutils  # noqa: F401
except ImportError:  # pragma: no cover
    try:
        import setuptools._distutils as _distutils

        sys.modules["distutils"] = _distutils
    except Exception:
        pass

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
        self._microphone_cache: list[str] | None = None
        self._microphone_devices: list[tuple[int | None, str]] | None = None
        self._last_voice_error: str | None = None
        self._last_backend_used: str = "uninitialized"

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
            self._last_voice_error = "speech_recognition package is not installed."
            return None
        recognizer = sr.Recognizer()
        backend_errors: list[str] = []
        try:
            if sd and np is not None:
                try:
                    heard = self._listen_with_sounddevice(recognizer, timeout=timeout, phrase_time_limit=phrase_time_limit)
                    self._last_voice_error = None
                    return heard
                except sr.WaitTimeoutError:
                    self._last_voice_error = None
                    return None
                except sr.UnknownValueError:
                    self._last_voice_error = None
                    return None
                except Exception as exc:
                    backend_errors.append(f"sounddevice: {self._format_exception(exc)}")

            heard = self._listen_with_microphone(recognizer, timeout=timeout, phrase_time_limit=phrase_time_limit)
            self._last_voice_error = None
            return heard
        except sr.WaitTimeoutError:
            self._last_voice_error = None
            return None
        except sr.UnknownValueError:
            self._last_voice_error = None
            return None
        except sr.RequestError as exc:
            message = f"Speech recognition backend error: {exc}"
            if message != self._last_voice_error:
                self.logger.warning(message)
                self._last_voice_error = message
            return None
        except Exception as exc:
            message = self._format_exception(exc)
            if backend_errors:
                message = f"{'; '.join(backend_errors)}; speech_recognition: {message}"
            if message != self._last_voice_error:
                self.logger.warning("Voice listen failed: %s", message)
                self._last_voice_error = message
            return None
        finally:
            if self.status_callback:
                self.status_callback(AssistantStatus.IDLE)

    def start_background_listening(self, on_text: Callable[[str], None]) -> bool:
        if not sr:
            self._last_voice_error = "speech_recognition package is not installed."
            self.logger.warning(self._last_voice_error)
            return False
        if self._listener_thread and self._listener_thread.is_alive():
            return True
        self._stop_event.clear()

        def runner() -> None:
            while not self._stop_event.is_set():
                heard = self.listen_once()
                if not heard:
                    time.sleep(0.8)
                    continue
                self._last_voice_error = None
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
        return True

    def stop_background_listening(self) -> None:
        self._stop_event.set()
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=1.0)

    def available_microphones(self) -> list[str]:
        if sd and np is not None:
            try:
                devices = []
                for index, device in enumerate(sd.query_devices()):
                    if device.get("max_input_channels", 0) > 0:
                        devices.append((index, str(device["name"])))
                self._microphone_devices = devices
                return [name for _, name in devices]
            except Exception as exc:  # pragma: no cover
                self.logger.warning("Sounddevice microphone enumeration failed: %s", exc)

        if not sr:
            return []
        if self._microphone_cache is None:
            try:
                self._microphone_cache = sr.Microphone.list_microphone_names()
            except Exception as exc:  # pragma: no cover
                self.logger.warning("Microphone enumeration failed: %s", exc)
                self._microphone_cache = []
        return self._microphone_cache

    def _selected_microphone_index(self) -> int | None:
        configured = self.settings.microphone_name.strip()
        if not configured:
            return None
        if self._microphone_devices:
            for index, name in self._microphone_devices:
                if configured.lower() in name.lower():
                    return index
        for index, name in enumerate(self.available_microphones()):
            if configured.lower() in name.lower():
                return index
        self.logger.warning("Configured microphone not found: %s", configured)
        return None

    def _listen_with_microphone(self, recognizer, timeout: int = 5, phrase_time_limit: int = 8) -> str | None:
        self._last_backend_used = "speech_recognition_microphone"
        with sr.Microphone(device_index=self._selected_microphone_index()) as source:
            if self.status_callback:
                self.status_callback(AssistantStatus.LISTENING)
            recognizer.dynamic_energy_threshold = True
            recognizer.adjust_for_ambient_noise(source, duration=0.6)
            recognizer.pause_threshold = 0.8
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            return recognizer.recognize_google(audio, language="en-IN").strip()

    def _listen_with_sounddevice(self, recognizer, timeout: int = 5, phrase_time_limit: int = 8) -> str | None:
        duration = max(2, min(int(phrase_time_limit or timeout or 8), 15))
        device_index = self._selected_microphone_index()
        if self.status_callback:
            self.status_callback(AssistantStatus.LISTENING)
        self._last_backend_used = "sounddevice"
        device_info = sd.query_devices(device_index, "input")
        sample_rate = int(device_info["default_samplerate"]) if device_info and device_info.get("default_samplerate") else 16000
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            device=device_index,
        )
        sd.wait()
        if not self._has_voice_activity(recording):
            return None
        audio = sr.AudioData(recording.tobytes(), sample_rate, 2)
        return recognizer.recognize_google(audio, language="en-IN").strip()

    def diagnostics(self) -> dict[str, object]:
        return {
            "speech_recognition_available": bool(sr),
            "sounddevice_available": bool(sd),
            "numpy_available": np is not None,
            "microphone_count": len(self.available_microphones()),
            "configured_microphone": self.settings.microphone_name or "system default",
            "backend": self._last_backend_used,
            "last_error": self._last_voice_error,
        }

    def last_error_message(self) -> str | None:
        return self._last_voice_error

    def _has_voice_activity(self, recording) -> bool:
        if np is None:
            return True
        try:
            peak = int(np.max(np.abs(recording)))
        except Exception:
            return True
        return peak > 250

    def _format_exception(self, exc: Exception) -> str:
        message = str(exc).strip()
        if message:
            return message
        return exc.__class__.__name__
