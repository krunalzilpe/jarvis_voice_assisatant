# Client Handoff Checklist

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set in `.env`:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL=https://api.openai.com/v1`

## Launch

Preferred:

- double-click `run_jarvis.bat`

Alternative:

- `python Jarvis\jarvis.py`

## Configure Before Delivery

- set the microphone from the Configuration tab
- set the assistant name and wake phrase if required
- configure OpenAI key for chat and image generation
- review permission toggles in the Permissions tab
- decide whether the client wants startup voice mode enabled

## Smoke Test

Run these commands or perform them from the UI:

- `notepad kholo`
- follow-up text entry
- `google pe python automation search karo`
- `youtube pe believer song baja`
- `screenshot lo`
- `binary search kya hota hai`
- `ek futuristic bike ka image generate karo`

## Delivery Notes

- `.env` is local-only and should not be committed
- `data/` stores runtime history, screenshots, and generated images
- `logs/` stores runtime logs
- AI chat and image generation require a valid funded OpenAI account
