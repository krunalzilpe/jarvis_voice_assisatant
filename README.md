# Windows Desktop AI Assistant

A Windows desktop assistant that combines practical system automation with full AI conversation. It can open and control apps, type into windows, search the browser, play YouTube results, capture screenshots, answer knowledge questions, help with coding and study tasks, and generate images when an OpenAI key is configured.

## Run Options

Fastest client-friendly launch:

- Double-click `run_jarvis.bat`
- Or double-click `Jarvis\jarvis.py`

Terminal launch:

```powershell
python Jarvis\jarvis.py
```

The launcher is bootstrap-aware:

- it detects a nearby `.venv`
- it relaunches through that interpreter when available
- it attempts dependency installation if imports are missing
- it shows a Windows error dialog instead of failing silently

## First-Time Setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

Then add your OpenAI key to `.env` if you want AI chat and image generation:

```env
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
```

## Product Features

- Voice control with wake phrase or always-listen mode
- AI chat for random questions, coding help, math, writing, translation, and explanations
- End-to-end Windows actions instead of partial opening-only behavior
- Browser search automation with typing and submit flow
- Notepad follow-up flow that asks what to type before typing it
- Image generation by text or voice prompt
- SQLite command history and file-based logs
- System tray support and background assistant lifecycle

## Using the App

- Home screen shows readiness, quick actions, last command, last action, and active window
- Configuration lets you set model, image model, API key, microphone, speaker, startup behavior, and tray mode
- Controls lets you start voice listening, pause, resume, stop, and run smoke actions
- AI Chat Box accepts normal questions and system commands in the same place
- Image Generation stores outputs in `data/generated_images`

## Voice Examples

- `Hey Jarvis, notepad kholo`
- `Hey Jarvis, google pe python automation search karo`
- `Hey Jarvis, youtube pe believer song baja`
- `Hey Jarvis, screenshot lo`
- `Hey Jarvis, binary search samjha`
- `Hey Jarvis, ek futuristic bike ka image generate karo`

## Project Paths

- Runtime settings and history: `data/`
- Logs: `logs/`
- Main launcher: `Jarvis/jarvis.py`
- One-click launcher: `run_jarvis.bat`
- Stress test: `scripts/automation_stress_test.py`

## Verification

Safe automation stress test:

```powershell
.\.venv\Scripts\python.exe scripts\automation_stress_test.py --iterations 10
```

Package compile check:

```powershell
.\.venv\Scripts\python.exe -m compileall jarvis_assistant
```

## License

MIT License

Copyright (c) 2026 Krunal
