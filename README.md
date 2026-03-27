# Windows Desktop AI Assistant

A modular, voice-enabled Windows assistant that combines real system control (apps, browser, typing, screenshots, volume, power) with full AI chat and image generation. Supports English, Hindi, and Hinglish, follow-up questions, and mixed requests (explain + act).

## Quick Start
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env   # add OPENAI_API_KEY if you want LLM/image
python Jarvis\jarvis.py       # or: python -m jarvis_assistant.main
```
Optional double-click launcher (`run_jarvis.bat`):
```bat
@echo off
call ..\.venv\Scripts\activate
python Jarvis\jarvis.py
```

## Using the App
- Controls tab: Start Assistant to enable voice agent; Pause/Resume/Stop as needed.
- AI Chat Box: type any command or question; see interpreted intent and actions.
- Image Generation: enter prompt, generate, view previews/history.
- Permissions: toggle app/browser/mouse/keyboard/clipboard/screenshot/power access and confirmations.
- Configuration: mic/speaker, wake phrase, models, tray/always-listen options.
- Status view: mode, last command/action, active window, background agent state.

## Voice Examples
- “Hey Jarvis, notepad kholo” → follow-up asks what to type, then types.
- “Hey Jarvis, google pe python automation search karo” → opens browser, types, submits.
- “Hey Jarvis, youtube pe believer song baja” → searches and plays.
- “Hey Jarvis, screenshot lo” → saves to `data/screenshots/`.
- Mixed: “Python automation kya hota hai aur Google pe search bhi kar do” → answers, then searches.
- Mixed: “Binary search samjha aur notepad me notes likh do” → explains, then types into Notepad.
- Images by voice: “Hey Jarvis, ek futuristic bike ka image generate karo” (needs `OPENAI_API_KEY`).

## Data & Logs
- Settings/DB/screenshots/images under `data/`
- Logs under `logs/`

## License
MIT © 2026 Krunal
