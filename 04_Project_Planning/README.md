# Phase 4 – Project Planning

| Stage | Work |
|---|---|
| 1 | Brainstorming and ideation |
| 2 | Requirement analysis |
| 3 | Architecture and UI design |
| 4 | FastAPI development |
| 5 | Gemini integration |
| 6 | Comic preview and PDF export |
| 7 | Testing and error handling |
| 8 | Documentation and demo |

## Risk Management

| Risk | Solution |
|---|---|
| Gemini quota | Cache identical requests and provide a safe fallback |
| API key exposure | Store key only in `.env` |
| Invalid AI JSON | Validate and normalize output |
| PDF wrapping error | Use `multi_cell` and safe text conversion |
| Double-click requests | Disable Generate button after submission |
