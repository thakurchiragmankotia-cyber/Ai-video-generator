# PRD — PropVid: AI Property Video Generator

## 1. Problem statement

A real estate sales team has photos and basic details for every listing, but making a separate
promotional video for each property means opening a video editor, writing copy, timing captions and
exporting by hand. That takes 30–60 minutes per listing, so most listings never get a video.

**PropVid** turns the details a sales agent already has (name, location, price, type, key features,
contact/CTA text and 4–8 photos) into a 20–40 second, ready-to-share MP4. Nobody has to open a video
editor.

## 2. Target users

| Persona | Who | Needs | Pain today |
|---|---|---|---|
| **Riya, sales executive** | Handles 15–25 active listings, shares on WhatsApp and Instagram | A video per listing in minutes, from her phone photos | No editing skills, no time |
| **Arjun, marketing coordinator** | Runs the agency's social pages | Consistent branded look, vertical format for Reels | Manually re-does the same template in an editor |
| **Meera, evaluator / developer** | Reviews or extends the tool | Runs it from a CLI with a JSON file, gets deterministic output | Needs clear setup and sample data |

## 3. Goals

1. Generate a coherent property video from a form or a JSON file with **zero manual editing**.
2. The script and captions use **only facts supplied in the input**, and this is checked automatically.
3. Output is a standard H.264/AAC MP4 that plays on WhatsApp, Instagram and in browsers.
4. Bad or missing input gives a **clear message, never a crash or stack trace**.
5. Works **offline and free by default**. The AI script writer is an optional upgrade.

## 4. Non-goals

- Not a general-purpose video editor (no timeline, no per-frame editing).
- No user accounts, database, hosting or multi-tenant features.
- No AI-generated images or video footage, and no virtual staging.
- No automatic posting to social networks.
- No multi-language voice-over in the MVP.

## 5. Features

### MVP (must-have)

| # | Feature |
|---|---|
| M1 | Input via a **Streamlit web form** (fields + 4–8 image upload) and a **CLI** that reads a JSON file |
| M2 | **Validation** with friendly messages: missing name, bad/corrupt images, too few or too many images, unsupported formats |
| M3 | **Script writer, template mode**: title, 3–5 feature scenes and CTA, built only from input facts |
| M4 | **Script writer, AI mode (optional)**: Claude writes the narration and captions; a **fact checker** rejects any output with unsupported numbers or claims and falls back to the template |
| M5 | **Scene builder**: images assigned to scenes, smart crop to frame, slow zoom/pan ("Ken Burns") |
| M6 | **Readable text overlays**: gradient backdrop, large bold captions, price tag, CTA card |
| M7 | **Crossfade transitions** between scenes |
| M8 | **Narration** with offline text-to-speech (on/off), scene length follows narration length |
| M9 | **Background music**: royalty-free ambient track generated in code (on/off), ducked under the voice |
| M10 | **MP4 export** with an in-app preview player and a download button. The CLI writes to a path |
| M11 | Vertical **720×1280** (default) or horizontal **1280×720** |
| M12 | A sample property (JSON + images) and at least one sample MP4 in the repo |

### V2 (should-have)

- Edit the generated captions and narration before rendering.
- Brand kit: logo watermark, agency colours, custom font.
- 1080p export preset, plus a square 1080×1080 format.
- Choice between several music moods.
- Batch mode: a CSV of listings produces one video per row.

### Later (nice-to-have)

- Neural or cloud TTS voices, Hindi and other regional languages.
- Subtitle (.srt) export alongside the MP4.
- Direct share to WhatsApp Business / Instagram.
- Auto-pick the best cover image with an image-quality model.

## 6. User stories

1. As a **sales executive**, I want to fill a short form and upload my photos, so that I get a shareable video without learning a video editor.
2. As a **sales executive**, I want the video to show the price, location and my contact number, so that viewers know how to enquire.
3. As a **sales executive**, I want a clear message when a photo is broken or a field is missing, so that I can fix it instead of seeing a crash.
4. As a **marketing coordinator**, I want every video to follow the same visual style, so that our brand looks consistent.
5. As a **marketing coordinator**, I want a vertical format, so that videos fit Reels, Shorts and WhatsApp Status.
6. As a **sales executive**, I want optional narration and music, so that the video feels finished.
7. As a **compliance-minded manager**, I want the script to state only facts we supplied, so that we never advertise something that isn't true.
8. As a **developer/evaluator**, I want a CLI with a JSON input, so that I can test the tool repeatably and script it.

## 7. Key user flows

### Flow A: web form (primary)
1. User runs `streamlit run app.py` and opens the local URL.
2. Optionally clicks **Load sample listing** to pre-fill the form.
3. Enters name, location, price, property type, features (one per line) and CTA/contact.
4. Uploads 4–8 images (JPG/PNG/WebP).
5. Chooses options: orientation, narration on/off, music on/off, AI script on/off.
6. Clicks **Generate video**. The app validates input; any problem appears as an inline message and nothing renders.
7. A progress bar shows the stages: script → images → audio → frames → encode.
8. The app shows the script used (and its source: template or AI), any warnings, the video player and a **Download MP4** button.

### Flow B: CLI
1. `python cli.py samples/sample_property.json -o output/video.mp4 [--horizontal] [--no-voice] [--no-music] [--ai]`
2. The CLI prints warnings, the script and the output path, and exits with code 0.
3. On invalid input it prints a readable error and exits with code 2. It never prints a traceback for user errors.

## 8. Success metrics

| Metric | Target |
|---|---|
| Time from filled form to MP4 (720p, 6 images, laptop) | < 90 s |
| Video length for a typical listing | 20–40 s |
| Videos needing manual edits before sharing | 0 |
| Unsupported facts in the final script (fact checker) | 0 |
| Crashes on malformed input in the test suite | 0 |
| Setup steps for a new user | ≤ 5 |

## 9. Risks, assumptions and open questions

**Risks**
- *LLM invents facts* ("sea view", "5 min to metro"). Mitigation: fact checker plus template fallback; AI is off by default.
- *Offline TTS sounds robotic*, and the voices differ by OS. Mitigation: narration is optional and music still plays; documented as a limitation.
- *Rendering is slow on weak machines.* Mitigation: 720p default, 24 fps, progress bar.
- *Mixed image sizes and orientations look bad.* Mitigation: EXIF-aware rotation and cover crop for every image.
- *Fonts differ by OS* (e.g. the ₹ glyph). Mitigation: font fallback chain; if no font can draw ₹, it is replaced with "Rs.".

**Assumptions**
- Images are owned by or licensed to the agency. The sample uses free-licensed or synthetic images.
- One property per video. The input is in English.
- The user runs the tool locally (no hosting needed for the assessment).

**Open questions** (decided for MVP, revisit later)
- Should agents edit the script before rendering? → V2.
- Which TTS for production quality? → evaluate cloud TTS later.
- Brand assets (logo, colours) per agency? → V2 brand kit.
