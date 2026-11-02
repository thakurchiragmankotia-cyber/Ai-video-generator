# AGENTS.md — rules for AI coding assistants in this repo

## Project summary
PropVid turns property details and 4–8 photos into a 20–40 s promotional MP4.
It has a Streamlit form (`app.py`) and a CLI (`cli.py`), and both call `propvid.pipeline.generate_video()`.
Scripts come from a template engine or, optionally, from Claude. AI output is fact-checked against the input.
Rendering is Pillow + NumPy frames, piped into ffmpeg through `imageio-ffmpeg`. Narration is offline TTS (pyttsx3).
Everything runs locally and offline by default, with no database and no server.

## Source of truth (in priority order)
1. `PRD.md`: what we build and why
2. `DESIGN.md`: every colour, font, size and timing
3. `ARCHITECTURE.md`: stack, folders, data flow, conventions
4. `PLAN.md`: build order and status

(`DATABASE.md` and `API.md` are intentionally absent. See ARCHITECTURE.md §1.)

## DO
- Follow the folder structure in ARCHITECTURE.md. Put new logic in the matching `propvid/` module.
- Reuse existing helpers (`fonts.load_font`, `images.cover_fit`, `theme` tokens) instead of re-implementing them.
- Write small, focused, typed functions. Keep validation and script logic pure and unit-testable.
- Comment non-obvious logic (timeline overlap, audio ducking, fact-check rules).
- Raise `InputError` for user mistakes, with a message that tells the user how to fix it.
- Add a warning, not an exception, for degradable problems (one bad image, TTS unavailable).
- Report progress through the `progress` callback for any step that takes more than about 1 s.
- Add or update tests in `tests/` for every behaviour change, and run `pytest` before finishing.

## DO NOT
- Do not change the tech stack or add a new library without asking first.
- Do not use any colour, font or size that is not in DESIGN.md / `propvid/theme.py`.
- Do not let AI-generated text reach the video without going through `fact_check()`.
- Do not invent property facts in templates. Only input fields can appear as facts.
- Do not hardcode secrets or API keys. Read them from env vars in `config.py`.
- Do not commit real customer data or photos you don't have rights to.
- Do not delete or rewrite working code unless asked.

## Workflow
1. **Plan:** state which PLAN.md task you are doing and which files you will touch.
2. **Code:** make the smallest change that completes the task. Keep the app runnable.
3. **Verify:** run `pytest` and, for rendering changes, `python cli.py samples/sample_property.json`.
4. **Explain:** give a short summary of what changed, why, and anything not verified.

If a request conflicts with PRD.md, DESIGN.md or ARCHITECTURE.md, **stop and ask** before proceeding.
