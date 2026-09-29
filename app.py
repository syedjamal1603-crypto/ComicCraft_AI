from __future__ import annotations
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fpdf import FPDF
from google import genai

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
EXPORT_DIR = BASE_DIR / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="ComicCraft AI", version="1.0.0")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Serve CSS, images, JavaScript, and other static files
STATIC_DIR = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
# Keep the model configurable. If your Google project uses another currently
# available Gemini text model, change GEMINI_MODEL in .env only.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

CACHE_FILE = EXPORT_DIR / "latest_comic.json"


def clean_text(value: Any, default: str = "") -> str:
    text = str(value if value is not None else default)
    text = text.replace("\x00", " ").strip()
    return text


def safe_latin1(value: Any) -> str:
    """Make text safe for the standard FPDF Helvetica font."""
    text = clean_text(value)
    replacements = {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u2026": "...",
        "\u00a0": " ", "\u2022": "-", "\u2192": "->",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


def normalize_comic(data: dict, user_input: dict) -> dict:
    """Guarantee a predictable 5-panel structure even if model output varies."""
    title = clean_text(data.get("title"), "ComicCraft Adventure")[:120]
    raw_panels = data.get("panels", [])
    if not isinstance(raw_panels, list):
        raw_panels = []

    panels = []
    for index in range(5):
        source = raw_panels[index] if index < len(raw_panels) and isinstance(raw_panels[index], dict) else {}
        panels.append({
            "panel_number": index + 1,
            "title": clean_text(source.get("title"), f"Scene {index + 1}")[:100],
            "scene_description": clean_text(
                source.get("scene_description"),
                f"{user_input['character']} is in {user_input['setting']}."
            )[:700],
            "narration": clean_text(
                source.get("narration"),
                "The story continues..."
            )[:500],
            "dialogue": clean_text(
                source.get("dialogue"),
                "Let's keep going!"
            )[:500],
            "image_prompt": clean_text(
                source.get("image_prompt"),
                f"Comic book panel of {user_input['character']} in {user_input['setting']}."
            )[:500],
        })

    return {
        "title": title,
        "character": user_input["character"],
        "setting": user_input["setting"],
        "tone": user_input["tone"],
        "art_style": user_input["art_style"],
        "panels": panels,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def demo_comic(user_input: dict) -> dict:
    """Offline fallback so the app still runs when Gemini quota/model access fails."""
    c = user_input["character"]
    s = user_input["setting"]
    tone = user_input["tone"]
    style = user_input["art_style"]

    scenes = [
        (
            "The Discovery",
            f"{c} arrives at {s} and notices a strange glowing signal.",
            f"{c} has no idea what is waiting ahead.",
            "What is that light?"
        ),
        (
            "The Mystery",
            f"{c} follows the signal and finds a mysterious device hidden nearby.",
            "The device begins to activate.",
            "I think I should investigate."
        ),
        (
            "The Challenge",
            f"A sudden challenge appears and {c} must make a quick decision.",
            f"The {tone.lower()} adventure becomes more intense.",
            "I have to stay calm and keep going!"
        ),
        (
            "The Turning Point",
            f"{c} discovers a clever way to solve the problem using the clues found earlier.",
            "One small idea changes everything.",
            "Now I know what to do!"
        ),
        (
            "The Ending",
            f"{c} solves the mystery and safely returns through {s}.",
            "The adventure ends with a new lesson and a promise of another journey.",
            "That was only the beginning..."
        ),
    ]

    panels = []
    for i, (title, scene, narration, dialogue) in enumerate(scenes, start=1):
        panels.append({
            "panel_number": i,
            "title": title,
            "scene_description": scene,
            "narration": narration,
            "dialogue": dialogue,
            "image_prompt": (
                f"{style} comic panel, {c}, {s}, scene {i}, "
                f"clear character pose, cinematic composition."
            ),
        })

    return normalize_comic({
        "title": f"{c}'s Adventure in {s}",
        "panels": panels,
    }, user_input)


def comic_cache_key(user_input: dict) -> str:
    raw = json.dumps(user_input, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_cached(user_input: dict) -> dict | None:
    if not CACHE_FILE.exists():
        return None
    try:
        saved = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if saved.get("_cache_key") == comic_cache_key(user_input):
            return saved.get("comic")
    except Exception:
        return None
    return None


def save_cached(user_input: dict, comic: dict) -> None:
    payload = {"_cache_key": comic_cache_key(user_input), "comic": comic}
    CACHE_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def generate_with_gemini(user_input: dict) -> dict:
    if client is None:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    prompt = f"""
Create a five-panel comic story.

User choices:
- Story idea: {user_input['story_prompt']}
- Main character: {user_input['character']}
- Setting: {user_input['setting']}
- Tone: {user_input['tone']}
- Art style: {user_input['art_style']}

Return ONLY valid JSON with this exact structure:
{{
  "title": "short comic title",
  "panels": [
    {{
      "title": "short panel title",
      "scene_description": "2-3 short sentences",
      "narration": "1 short sentence",
      "dialogue": "1 short line of dialogue",
      "image_prompt": "short visual prompt under 300 characters"
    }}
  ]
}}

Rules:
- Exactly 5 panels.
- Keep all text concise.
- No markdown.
- No code fences.
- Keep image_prompt under 300 characters.
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING"},
                    "panels": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "title": {"type": "STRING"},
                                "scene_description": {"type": "STRING"},
                                "narration": {"type": "STRING"},
                                "dialogue": {"type": "STRING"},
                                "image_prompt": {"type": "STRING"},
                            },
                            "required": [
                                "title",
                                "scene_description",
                                "narration",
                                "dialogue",
                                "image_prompt",
                            ],
                        },
                    },
                },
                "required": ["title", "panels"],
            },
        },
    )

    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini returned an empty response.")

    return json.loads(text)


def create_pdf(comic: dict) -> Path:
    filename = f"comic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = EXPORT_DIR / filename

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.multi_cell(0, 10, safe_latin1(comic["title"]))
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 10)
    meta = (
        f"Character: {comic['character']} | Setting: {comic['setting']} | "
        f"Tone: {comic['tone']} | Art Style: {comic['art_style']}"
    )
    pdf.multi_cell(0, 6, safe_latin1(meta))
    pdf.ln(5)

    for panel in comic["panels"]:
        pdf.set_font("Helvetica", "B", 13)
        pdf.multi_cell(0, 8, safe_latin1(
            f"Panel {panel['panel_number']}: {panel['title']}"
        ))

        pdf.set_font("Helvetica", "", 10)
        fields = [
            ("Scene", panel["scene_description"]),
            ("Narration", panel["narration"]),
            ("Dialogue", panel["dialogue"]),
            ("Image Prompt", panel["image_prompt"]),
        ]
        for label, value in fields:
            pdf.set_font("Helvetica", "B", 10)
            pdf.write(6, safe_latin1(f"{label}: "))
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, safe_latin1(value))
            pdf.ln(1)
        pdf.ln(5)

    pdf.output(str(filepath))
    return filepath


def build_user_input(
    story_prompt: str,
    character: str,
    setting: str,
    tone: str,
    art_style: str,
) -> dict:
    return {
        "story_prompt": clean_text(story_prompt)[:1200],
        "character": clean_text(character, "Alex")[:100],
        "setting": clean_text(setting, "Futuristic Chennai")[:120],
        "tone": clean_text(tone, "Adventure")[:80],
        "art_style": clean_text(art_style, "Comic Book")[:100],
    }


def make_comic(user_input: dict) -> tuple[dict, str]:
    cached = load_cached(user_input)
    if cached:
        return cached, "cached"

    try:
        raw = generate_with_gemini(user_input)
        comic = normalize_comic(raw, user_input)
        save_cached(user_input, comic)
        return comic, "gemini"
    except Exception as exc:
        # Do not crash the application on quota, model, network, or JSON errors.
        comic = demo_comic(user_input)
        comic["notice"] = (
            "Demo fallback was used because Gemini was unavailable. "
            f"Reason: {type(exc).__name__}"
        )
        save_cached(user_input, comic)
        return comic, "fallback"


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "model": GEMINI_MODEL},
    )


@app.post("/generate", response_class=HTMLResponse)
async def generate(
    request: Request,
    story_prompt: str = Form(...),
    character: str = Form(...),
    setting: str = Form(...),
    tone: str = Form(...),
    art_style: str = Form(...),
):
    user_input = build_user_input(
        story_prompt, character, setting, tone, art_style
    )
    if not user_input["story_prompt"]:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "model": GEMINI_MODEL,
                "error": "Please enter a story prompt.",
            },
            status_code=400,
        )

    comic, source = make_comic(user_input)
    return templates.TemplateResponse(
        "comic_preview.html",
        {
            "request": request,
            "comic": comic,
            "source": source,
        },
    )


@app.post("/generate-comic/json")
async def generate_json(payload: dict):
    user_input = build_user_input(
        payload.get("story_prompt", ""),
        payload.get("character", "Alex"),
        payload.get("setting", "Futuristic Chennai"),
        payload.get("tone", "Adventure"),
        payload.get("art_style", "Comic Book"),
    )
    if not user_input["story_prompt"]:
        return JSONResponse(
            {"error": "story_prompt is required."}, status_code=400
        )

    comic, source = make_comic(user_input)
    return JSONResponse({"source": source, "comic": comic})


@app.post("/export")
async def export_pdf(payload: dict):
    comic = payload.get("comic")
    if not isinstance(comic, dict):
        return JSONResponse({"error": "Invalid comic data."}, status_code=400)

    # Normalize again so malformed client-side data cannot break the PDF.
    user_input = {
        "story_prompt": "",
        "character": clean_text(comic.get("character"), "Alex"),
        "setting": clean_text(comic.get("setting"), "Unknown"),
        "tone": clean_text(comic.get("tone"), "Adventure"),
        "art_style": clean_text(comic.get("art_style"), "Comic Book"),
    }
    normalized = normalize_comic(comic, user_input)
    pdf_path = create_pdf(normalized)

    return {
        "filename": pdf_path.name,
        "download_url": f"/download/{pdf_path.name}",
    }


@app.get("/download/{filename}")
async def download(filename: str):
    # Prevent path traversal.
    safe_name = Path(filename).name
    path = EXPORT_DIR / safe_name
    if not path.exists() or path.suffix.lower() != ".pdf":
        return JSONResponse({"error": "File not found."}, status_code=404)
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=safe_name,
    )


@app.get("/export-success", response_class=HTMLResponse)
async def export_success(request: Request, filename: str = ""):
    return templates.TemplateResponse(
        "export_success.html",
        {"request": request, "filename": filename},
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "gemini_configured": bool(GEMINI_API_KEY),
        "model": GEMINI_MODEL,
        "cache_exists": CACHE_FILE.exists(),
    }


@app.get("/test-image")
async def test_image():
    # The reference project includes this route. This implementation returns
    # a safe status message rather than calling an additional image API.
    return {
        "status": "available",
        "message": (
            "ComicCraft currently generates image prompts and a visual comic "
            "layout without consuming a separate image-generation quota."
        ),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
