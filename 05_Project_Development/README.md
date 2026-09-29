# Phase 5 – Project Development

## Backend
`app.py` implements:
- FastAPI application
- Gemini integration
- JSON structured output
- Five-panel normalization
- Local caching
- PDF export
- API error handling

## Frontend
- `templates/index.html`
- `templates/comic_preview.html`
- `templates/export_success.html`
- `static/style.css`

## Main Routes
- `/`
- `/generate`
- `/generate-comic/json`
- `/export`
- `/download/{filename}`
- `/export-success`
- `/health`
- `/test-image`

## Security
The API key is read from `.env` and is excluded from GitHub by `.gitignore`.
