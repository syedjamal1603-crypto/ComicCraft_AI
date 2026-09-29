# Phase 3 – Project Design

## Architecture

```text
Browser
  |
  v
HTML/CSS/Jinja2
  |
  v
FastAPI
  |
  +----> Gemini API
  |
  +----> Local Cache
  |
  +----> PDF Export
```

## User Flow

```text
Open homepage
     ↓
Enter story details
     ↓
Submit
     ↓
FastAPI
     ↓
Gemini / cached result
     ↓
Five comic panels
     ↓
Preview
     ↓
Local PDF export
```

## Modules
- UI module
- FastAPI routing module
- Gemini generation module
- Cache module
- PDF export module
- Error/fallback module
