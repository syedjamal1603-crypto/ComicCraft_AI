# ComicCraft AI – SmartBridge Project

ComicCraft is a FastAPI web application that turns a user's story idea and preferences into a five-panel comic story using the Gemini API.

## Current project structure

- `app.py` – FastAPI backend and Gemini integration
- `templates/` – web pages
- `static/` – CSS
- `exports/` – generated local output
- `01_...` through `08_...` – SmartBridge phase documentation

## Run in VS Code

```bash
python -m venv env
```

Windows PowerShell:

```powershell
.\env\Scripts\Activate.ps1
```

Install:

```bash
pip install -r requirements.txt
```

Create `.env` from `.env.example` and add your Gemini API key.

Run:

```bash
python app.py
```

Open:

`http://127.0.0.1:8000/`

API docs:

`http://127.0.0.1:8000/docs`

Health check:

`http://127.0.0.1:8000/health`

## Important quota protection

The app caches the latest successful comic in `exports/latest_comic.json`. Repeating the same request does not make another Gemini call.

If Gemini is unavailable because of quota, rate limits, a temporary network error, or model access, the app uses a built-in demo fallback instead of crashing. This keeps the local demonstration flow usable, but the fallback is not AI-generated.

## Security

Never commit `.env` or a real API key to GitHub. `.gitignore` already excludes `.env`.

## GitHub

After testing locally:

```bash
git init
git add .
git commit -m "ComicCraft SmartBridge project"
git branch -M main
git remote add origin YOUR_PUBLIC_REPOSITORY_URL
git push -u origin main
```
