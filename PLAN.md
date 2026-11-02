# PLAN — implementation roadmap

Each phase leaves the app runnable. The build goes in vertical slices: the CLI can render a silent
video by the end of phase 1, and each later phase adds to that video.

## Phase 0: Foundation
- [x] **0.1 Repo + env.** `git init`, `.gitignore`, `requirements*.txt`, `.env.example`, venv.
  Verify: `pip install -r requirements-dev.txt` succeeds.
- [x] **0.2 Docs.** PRD, DESIGN, ARCHITECTURE, AGENTS, PLAN. Verify: reviewed with the user.

**Done when:** dependencies install and `python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"` prints a path.

## Phase 1: Silent video slice (depends on 0)
- [x] **1.1 Models + errors** (`models.py`, `errors.py`). Verify: imports cleanly.
- [x] **1.2 Validation** (`validation.py`): required fields, feature list parsing, image count rules. Verify: `tests/test_validation.py`.
- [x] **1.3 Images** (`images.py`): open/verify, EXIF transpose, cover-fit, placeholders. Verify: `tests/test_images.py` (corrupt file → warning).
- [x] **1.4 Template script** (`script_writer.py`). Verify: `tests/test_script_writer.py`: title, 3–5 features, CTA, only input facts.
- [x] **1.5 Theme + fonts + overlays** (`theme.py`, `fonts.py`, `overlays.py`). Verify: save the overlay PNGs and inspect them.
- [x] **1.6 Renderer** (`renderer.py`): timeline, Ken Burns, crossfade, encode. Verify: `tests/test_renderer.py` renders a tiny clip.
- [x] **1.7 Pipeline + CLI** (`pipeline.py`, `cli.py`). Verify: `python cli.py samples/sample_property.json --no-voice --no-music` writes an MP4.

**Done when:** the CLI produces a silent MP4 with captions and transitions from the sample JSON.

## Phase 2: Audio (depends on 1)
- [x] **2.1 Music generator** (`audio.py`). Verify: the WAV plays and loops cleanly, with fade in/out.
- [x] **2.2 TTS per scene + durations.** Verify: scene length follows narration; failure → warning.
- [x] **2.3 Mix + mux** (ducking, AAC). Verify: the MP4 has an audio stream and the voice is audible over the music.

**Done when:** the sample MP4 has narration and music, in sync with the scenes.

## Phase 3: AI script (depends on 1.4)
- [x] **3.1 Claude call** with structured JSON output, model from env. Verify: runs with a key; without a key → template + info message.
- [x] **3.2 Fact checker.** Verify: `tests/test_fact_check.py` rejects invented numbers and unknown amenities.
- [x] **3.3 Fallback wiring.** Verify: a forced failure falls back to the template with a warning.

**Done when:** `--ai` works with a key, and invented facts never reach the video.

## Phase 4: Web UI (depends on 1–3)
- [x] **4.1 Form + sample loader** (`app.py`, `.streamlit/config.toml`). Verify: the form pre-fills from the sample.
- [x] **4.2 Generate + progress + preview + download.** Verify: the browser shows the player and the download works.
- [x] **4.3 Error display.** Verify: no images or a missing name shows `st.error`, with no traceback.

**Done when:** a user can go from form to downloaded MP4 in the browser.

## Phase 5: Polish + submission
- [x] **5.1 Sample assets + sample MP4s** (vertical + horizontal). Verify: files exist in `samples/output/`.
- [x] **5.2 Tests green.** Verify: `pytest` passes.
- [x] **5.3 README + SETUP** (approach, decisions, limitations, models/libraries used). Verify: a fresh-venv walkthrough works.

**Done when:** every item on the assignment's "What to Submit" list is in the repo.
