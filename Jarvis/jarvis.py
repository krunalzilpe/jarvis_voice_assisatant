from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox


ROOT = Path(__file__).resolve().parents[1]
VENV_CANDIDATES = (
    ROOT / ".venv" / "Scripts" / "python.exe",
    ROOT.parent / ".venv" / "Scripts" / "python.exe",
)
BOOTSTRAP_ENV = "JARVIS_BOOTSTRAPPED"


def _show_error(title: str, body: str) -> None:
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, body)
        root.destroy()
    except Exception:
        print(f"{title}: {body}", file=sys.stderr)


def _relaunch_with_venv() -> None:
    if os.environ.get(BOOTSTRAP_ENV) == "1":
        return

    current_python = Path(sys.executable).resolve()
    for candidate in VENV_CANDIDATES:
        if candidate.exists() and current_python != candidate.resolve():
            env = os.environ.copy()
            env[BOOTSTRAP_ENV] = "1"
            completed = subprocess.run(
                [str(candidate), str(Path(__file__).resolve())],
                cwd=str(ROOT),
                env=env,
                check=False,
            )
            raise SystemExit(completed.returncode)


def _ensure_importable() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    try:
        import jarvis_assistant.main  # noqa: F401
        return
    except ModuleNotFoundError:
        requirements = ROOT / "requirements.txt"
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(requirements)],
                cwd=str(ROOT),
                check=True,
            )
        except Exception as exc:
            _show_error(
                "Jarvis Startup Error",
                "Dependencies could not be installed automatically.\n\n"
                f"Python: {sys.executable}\n"
                f"Requirements: {requirements}\n\n"
                f"Error: {exc}",
            )
            raise SystemExit(1) from exc


def main() -> None:
    _relaunch_with_venv()
    _ensure_importable()

    from jarvis_assistant.main import main as app_main

    try:
        app_main()
    except Exception as exc:
        _show_error(
            "Jarvis Runtime Error",
            "The assistant failed during startup.\n\n"
            f"Python: {sys.executable}\n"
            f"Working directory: {ROOT}\n\n"
            f"Error: {exc}",
        )
        raise


if __name__ == "__main__":
    main()
