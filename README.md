# PropVid: AI Property Video Generator

Turn property details and 4–8 photos into a **20–40 second, ready-to-share MP4**, with captions,
transitions, narration and music. It runs from a web form or the command line, and no video editor is needed.

| Vertical (default, 720×1280) | Horizontal (1280×720) |
|---|---|
| `samples/output/skyline_residency_vertical.mp4` | `samples/output/skyline_residency_horizontal.mp4` |

> Screenshot placeholders: `docs/screenshot-form.png`, `docs/screenshot-result.png` (add your own after running the app).

## Key features

- **Two ways in:** a Streamlit web form (upload photos, preview, download) and a CLI that reads a JSON file.
- **Script writer:** an offline template writer by default. An optional **Claude** writer produces livelier copy,
  and its output is **fact-checked against your input**, so invented claims never reach the video.
- **Scenes:** an opening title, 3–5 feature scenes (plus extra photo scenes when you have more photos), and a closing enquiry card.
- **Visuals:** smart crop for any photo size or orientation (EXIF-aware), slow zoom/pan, crossfades, and
  readable captions on a gradient scrim. The design tokens are in [DESIGN.md](DESIGN.md).
- **Audio:** offline text-to-speech narration (scene length follows the voice) and a royalty-free music
  track generated in code, which gets quieter while the narrator speaks.
- **Graceful errors:** broken, missing or too few photos, and missing price, location or contact,
  produce clear warnings. A missing property name gives a clear error. The app never shows a stack trace.

## Tech stack

Python 3.10+, Streamlit, Pillow, NumPy, imageio-ffmpeg (ships an ffmpeg binary), pyttsx3, and the
Anthropic SDK (optional). See [ARCHITECTURE.md](ARCHITECTURE.md) for why each was chosen.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py            # then click "Load sample listing" → "Generate video"
python cli.py samples/sample_property.json -o output/skyline.mp4   # CLI alternative
```

There are more details, plus fixes for common setup errors, in [SETUP.md](SETUP.md).

## CLI usage

```
python cli.py INPUT.json [-o OUT.mp4] [--horizontal] [--no-voice] [--no-music] [--ai] [--fps N] [--debug]
```

The input JSON looks like this (image paths are relative to the JSON file):

```json
{
  "name": "Skyline Residency",
  "location": "Whitefield, Bengaluru",
  "price": "₹85 Lakh",
  "property_type": "2 BHK Apartment",
  "features": ["1,150 sq ft carpet area with a spacious living room", "Modular kitchen with built-in chimney"],
  "cta": "Book your site visit today",
  "contact": "Call +91 90000 00000 or email sales@example.com",
  "images": ["images/01_exterior.jpg", "images/02_living_room.jpg"]
}
```

Only `name` is required. Exit codes: `0` success, `2` input problem (message printed), `1` unexpected error.

## Sample input and output

| File | What it shows |
|---|---|
| `samples/sample_property.json` | Complete listing with 6 photos, producing `samples/output/skyline_residency_*.mp4` |
| `samples/sample_incomplete.json` | No price, no CTA, 2 features, a missing photo and a non-image file. The video is still made, with warnings (`palm_grove_incomplete_input.mp4` + `.log`) |
| `samples/sample_invalid.json` | No property name. The tool stops with a clear error and exit code 2 (`invalid_input.log`) |
| `samples/CREDITS.md` | Licences for the sample photos (Wikimedia Commons, CC0 / CC BY / CC BY-SA) |

## Environment variables

| Name | Purpose | Example |
|---|---|---|
| `ANTHROPIC_API_KEY` | Enables the optional AI script writer. Without it, the template writer is used | `sk-ant-...` |
| `PROPVID_CLAUDE_MODEL` | Claude model for AI scripts | `claude-opus-5-5` |
| `PROPVID_FPS` | Output frame rate (12–60) | `24` |

Copy `.env.example` to `.env` to set them. Never commit `.env`.

## How it works

```
input (form / JSON) → validation → images (verify, rotate, crop)
                    → script (template, or Claude + fact check → template fallback)
                    → narration per scene (pyttsx3) → scene durations
                    → music + mix (ducking) → frames (zoom/pan, overlays, crossfades) → ffmpeg H.264/AAC MP4
```

### Approach and key decisions

- **Only supplied facts.** Both writers fill a fixed scene structure that we control: title, one scene per
  feature, CTA. The template writer copies input fields verbatim. The AI writer may only rephrase, and
  `fact_check()` rejects its output if it contains:
  - numbers or number words that are not in the input,
  - property claims that are not in the input, such as "pool", "metro", "sea view" or "parking",
  - superlatives such as "best" or "guaranteed",
  - captions that no longer match their feature,
  - text that is too long for the screen.

  Any rejection, API error or missing key falls back to the template, with a warning that says why.
- **The AI is optional, and off by default.** The tool works fully offline and for free. The task allows a justified
  rule-based approach, and for short listing copy a template is predictable and always truthful. Claude adds
  variety and warmth when a key is available.
- **No MoviePy.** Frames are drawn with Pillow and piped straight into ffmpeg. This avoids MoviePy's
  version-specific APIs and ImageMagick, and gives exact control over the text layout.
- **Narration drives timing.** Each scene lasts as long as its voice-over plus a short pause, so the voice and
  visuals never drift apart.
- **Royalty-free by construction.** The music is synthesised from sine waves, so there are no licensing
  questions. The sample photos come with their licences in `samples/CREDITS.md`.

### What the AI does, what it sees, and how it is checked

| | |
|---|---|
| Model | Claude (`claude-opus-5-5` by default, via the Anthropic Python SDK), structured JSON output, low effort |
| Input it sees | Only the listing fields you entered (name, location, price, type, features, CTA, contact). No photos and no personal data beyond the contact text |
| Output | Title narration, a caption + narration for each feature, and the CTA caption + narration |
| Checks | `fact_check()` (numbers, claim terms, superlatives, feature alignment, length). The scene structure and images are never AI-controlled |

### Limitations

- Offline TTS voices sound robotic and differ by OS (Windows SAPI5, macOS NSSpeechSynthesizer, Linux eSpeak).
  If no engine is available, the video is made with music only, and you get a warning.
- The fact checker is rule-based and errs on the strict side. Unusual but valid phrasing can be rejected,
  and the tool then falls back to the template.
- Template narration reads features as short ad-style lines. It cannot add words like "a" or "the" safely.
- Rendering is CPU-bound: about 45–60 s for a 35 s 720p video on a typical laptop. There is no 1080p preset yet.
- English only. A single fixed visual theme (brand kits are planned for V2, see [PRD.md](PRD.md)).

## Libraries, models and services used

| Name | Use | Licence |
|---|---|---|
| Streamlit | Web UI | Apache 2.0 |
| Pillow | Image loading, text and overlay drawing | MIT-CMU (HPND) |
| NumPy | Frame blending, audio synthesis and mixing | BSD |
| imageio-ffmpeg + bundled FFmpeg | H.264/AAC encoding and muxing | BSD-2 / LGPL-GPL (FFmpeg) |
| pyttsx3 | Offline text-to-speech through OS voices | MPL-2.0 |
| python-dotenv | Loads `.env` | BSD |
| Anthropic Python SDK + Claude API | Optional AI script writer | MIT (SDK); API under Anthropic terms |
| pytest | Tests | MIT |
| Wikimedia Commons | Sample photos | per image, see `samples/CREDITS.md` |

## Project structure

```
app.py, cli.py          entry points (web form, command line)
propvid/                pipeline package: validation, images, script_writer, fonts, overlays, audio, renderer, pipeline
samples/                sample JSON, photos, rendered MP4s and logs
tests/                  pytest suite (validation, images, script/fact check, rendering end to end)
*.md                    PRD, DESIGN, ARCHITECTURE, AGENTS, PLAN, SETUP
```

## Scripts

| Command | What it does |
|---|---|
| `streamlit run app.py` | Start the web app on http://localhost:8501 |
| `python cli.py samples/sample_property.json` | Render the sample to `output/sample_property.mp4` |
| `python -m pytest` | Run the test suite (install `requirements-dev.txt` first) |

There is no build or lint step. The project is plain Python.

## Demo

1. `streamlit run app.py` → **Load sample listing** → **Generate video**. Watch the progress bar, then play and download the MP4.
2. Clear the price and upload only 2 photos → generate → warnings appear, and the video is still made.
3. Clear the property name → generate → a clear "Please fix the input" message, with no crash.
4. `python cli.py samples/sample_invalid.json` → a readable error and exit code 2.

## Contributing and licence

Read [AGENTS.md](AGENTS.md) and [PLAN.md](PLAN.md) first. Keep to the folder structure and design tokens, and add
tests for any behaviour change. The code is MIT-licensed. The sample photos keep their own licences (see `samples/CREDITS.md`).
