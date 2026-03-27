# Jarvis Voice Assistant for Windows

A production-style Windows desktop assistant that combines AI conversation with practical local computer control.

It supports:

- natural language commands in English, Hindi, and Hinglish
- general AI answering for study, coding, writing, reasoning, and random questions
- Windows app control
- browser automation with typed search and result flow
- Notepad follow-up typing
- screenshots, clipboard-aware typing, and window focus control
- image generation when a valid OpenAI key is configured
- background voice mode and tray-aware desktop UI

## Highlights

- End-to-end task execution instead of open-only shortcuts
- Mixed intent support such as explanation plus Google search
- Follow-up question handling when user input is incomplete
- SQLite command history and log files
- One-click Windows launcher
- Configurable permissions for browser control, typing, screenshots, and power actions

## Quick Start

### One-click launch

Double-click:

- `run_jarvis.bat`

or:

- `Jarvis\jarvis.py`

### Terminal launch

```powershell
python Jarvis\jarvis.py
```

The launcher is bootstrap-aware:

- it detects a nearby `.venv`
- it relaunches with that interpreter when available
- it attempts dependency installation if imports are missing
- it shows a Windows dialog for startup/runtime failures instead of silently crashing

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

Add your OpenAI configuration to `.env` if you want AI chat or image generation:

```env
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
```

AI chat and image generation require a valid OpenAI key with active credits or billing.

## Core Features

### AI Assistant

- general questions and conversation
- coding help and debugging help
- math, logic, and explanation requests
- writing help, summaries, and translation
- mixed requests such as explain plus search

### Windows Automation

- open and close apps
- focus windows
- open folders
- type into active apps
- browser navigation
- Google search flow
- YouTube search and playback flow
- screenshot capture
- volume control
- guarded power actions with confirmation

### Voice and UI

- wake phrase mode
- always-listen mode
- microphone selection
- desktop control panel
- tray-aware close behavior
- chat box
- image generation panel
- command history view

## Example Commands

- `Hey Jarvis, notepad kholo`
- `Hey Jarvis, google pe python automation search karo`
- `Hey Jarvis, youtube pe believer song baja`
- `Hey Jarvis, screenshot lo`
- `Hey Jarvis, binary search samjha`
- `Hey Jarvis, python automation kya hota hai aur google pe search bhi kar do`
- `Hey Jarvis, ek futuristic bike ka image generate karo`

## Desktop Interface

The UI includes:

- `Home / Status`
- `Configuration`
- `Customization`
- `Permissions`
- `Controls`
- `AI Chat Box`
- `Image Generation`

## Project Structure

- `Jarvis/jarvis.py` - compatibility launcher and bootstrap entry point
- `run_jarvis.bat` - one-click Windows launcher
- `jarvis_assistant/` - assistant package
- `scripts/automation_stress_test.py` - safe mocked stress validation
- `scripts/live_smoke_test.py` - real desktop smoke automation
- `tests/` - unit tests for routing, follow-up logic, and storage
- `data/` - runtime settings, SQLite history, screenshots, generated images
- `logs/` - runtime log files

## Validation

Run the main validation commands:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\automation_stress_test.py --iterations 10
.\.venv\Scripts\python.exe scripts\live_smoke_test.py --youtube
```

## Client Delivery Notes

- keep `.env` local and never commit it
- configure the microphone and OpenAI key before delivery
- verify browser automation on the target client machine
- verify Windows microphone privacy permissions are enabled
- verify power-action permissions match the client requirement

See `CLIENT_HANDOFF.md` for a short deployment checklist.

## License

MIT License

Copyright (c) 2026 Krunal
