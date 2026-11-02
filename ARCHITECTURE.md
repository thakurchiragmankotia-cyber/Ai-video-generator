# ARCHITECTURE — PropVid

## 1. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.10+ | Required by the task; strong imaging and audio libraries |
| UI | Streamlit | A form, file upload, progress bar and video preview in ~150 lines, with no frontend build |
| CLI | `argparse` (stdlib) | No extra dependency; easy to script and test |
| Images and text overlays | Pillow | Precise control of fonts, wrapping, gradients and EXIF rotation |
| Frame math | NumPy | Fast blending for crossfades and audio mixing |
| Video encoding | `imageio-ffmpeg` (bundled ffmpeg binary) | `pip install` ships ffmpeg, so there is nothing to install system-wide on Windows/Mac/Linux |
| Narration | `pyttsx3` (offline TTS: SAPI5 / NSSpeechSynthesizer / eSpeak) | Free, no API key, works offline |
| Music | Generated in code with NumPy (ambient chord pad) | Royalty-free by construction, no download |
| AI script (optional) | Anthropic Python SDK, model `claude-opus-5-5`, structured JSON output | A reliable JSON schema, and the output is fact-checked before use |
| Storage | Local filesystem only | No database is needed. Inputs are files and the output is an MP4 |
| Hosting | Runs locally | The assessment needs a runnable prototype, not a deployment |

**Decision: no MoviePy.** I first planned to use MoviePy, but switched to writing frames straight into
ffmpeg through `imageio-ffmpeg`. MoviePy 1.x and 2.x have different, breaking APIs, and the
text-rendering path depends on ImageMagick. Our own small renderer is easier to test and gives exact
control over the overlays. ffmpeg still does all the encoding and audio muxing.

**No database and no REST API.** The PRD has no persistent entities or remote clients, so `DATABASE.md`
and `API.md` from the generic doc plan are deliberately left out. The "API" is the Python function
`propvid.pipeline.generate_video()`, which both the UI and the CLI call.

## 2. Folder structure

```
.
├── app.py                    # Streamlit UI (form → generate_video → preview/download)
├── cli.py                    # CLI entry: JSON in, MP4 out
├── propvid/
│   ├── __init__.py
│   ├── config.py             # RenderOptions, frame sizes, env settings
│   ├── theme.py              # Design tokens from DESIGN.md (colours, sizes, timings)
│   ├── models.py             # PropertyInput, Scene, Script dataclasses
│   ├── errors.py             # InputError (user-facing) and helpers
│   ├── validation.py         # Parse + validate raw input → PropertyInput + warnings
│   ├── images.py             # Load/verify images, EXIF fix, cover-crop, placeholders
│   ├── script_writer.py      # Template script + AI script + fact checker
│   ├── fonts.py              # Font fallback chain and glyph checks
│   ├── overlays.py           # Pillow drawing of scrim, captions, price tag, CTA card
│   ├── audio.py              # TTS per scene, generated music, mixing, WAV I/O
│   ├── tts_worker.py         # pyttsx3 runs in a subprocess (OS speech engines misbehave in Streamlit threads)
│   ├── renderer.py           # Timeline, Ken Burns, crossfades, ffmpeg encode + mux
│   └── pipeline.py           # generate_video(): orchestrates everything, reports progress
├── samples/
│   ├── sample_property.json
│   ├── sample_incomplete.json  # missing price/CTA, bad image paths → warnings, still renders
│   ├── sample_invalid.json     # no name → clear error, exit code 2
│   ├── images/               # sample photos (free licence, see samples/CREDITS.md)
│   └── output/               # sample MP4s and CLI logs produced by the tool
├── tests/                    # pytest suite
├── .streamlit/config.toml    # UI theme tokens
├── .env.example
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── LICENSE
└── PRD.md, DESIGN.md, ARCHITECTURE.md, AGENTS.md, PLAN.md, README.md, SETUP.md
```

## 3. Data flow

```
Form (app.py) ─┐                                  ┌─► Claude API (optional, AI mode)
               ├─► validation ─► PropertyInput ─► script_writer ─► fact_check ─┐
JSON (cli.py) ─┘        │                           (template fallback) ◄──────┘
                        ▼                                   │ Script (scenes: caption, narration)
                     images ─► list[Image]                  ▼
                        │                    audio: pyttsx3 per scene → durations
                        │                           + generated music → mixed WAV
                        ▼                                   │
                 renderer: timeline from durations ◄────────┘
                   per frame: Ken Burns crop → overlay → crossfade
                   → ffmpeg (imageio-ffmpeg) H.264 → mux with AAC audio → MP4
```

Scene durations come from the narration length, so the voice and visuals always stay in sync. Without
narration, the fixed durations from DESIGN.md are used.

## 4. State and errors

- **State:** stateless pipeline. The Streamlit app keeps only the form values and the last result in
  `st.session_state`. Each render uses a fresh temporary directory, deleted afterwards.
- **User errors** (bad input) raise `InputError` with a readable message. The UI shows it with
  `st.error` and the CLI prints it and exits with code 2.
- **Degradable failures** add a warning and continue: a corrupt single image, the TTS engine
  missing, an AI call failing, or the fact check rejecting AI output.
- **Unexpected errors:** the UI shows a short message plus an expandable traceback. The CLI exits
  with code 1 and suggests `--debug`.
- **Progress:** `generate_video(..., progress=callback)` reports `(fraction, stage_label)`.

## 5. Conventions

- PEP 8, type hints, `snake_case` functions, `PascalCase` dataclasses, module-level constants in `UPPER_CASE`.
- Small pure functions where possible (validation, script writing and layout are pure and unit-tested).
- No secrets in code. Environment variables are read in `config.py` only.

| Env var | Purpose | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Enables AI script mode | unset → template only |
| `PROPVID_CLAUDE_MODEL` | Model for AI script mode | `claude-opus-5-5` |
| `PROPVID_FPS` | Output frame rate | `24` |

## 6. Performance and scalability

- 720×1280 at 24 fps for a 30 s video is about 720 frames. The Ken Burns step works on an image that
  is pre-scaled once per scene, so each frame needs only one crop and one resize (~10 ms).
- Overlays are drawn once per scene and alpha-composited per frame.
- ffmpeg encodes with `libx264 -preset medium -crf 20 -pix_fmt yuv420p` and `+faststart` for web playback.
- Scaling out (batch/V2): `generate_video` is a pure function of its inputs, so a queue of
  listings can run in parallel processes without shared state.
