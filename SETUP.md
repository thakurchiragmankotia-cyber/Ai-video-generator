# SETUP: run PropVid locally

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.10 – 3.13 (tested on 3.13) | `python --version` |
| pip | 23+ | ships with Python |
| FFmpeg | **not needed** | `imageio-ffmpeg` installs its own binary |
| Speech engine (optional, for narration) | Windows: built in (SAPI5) · macOS: built in · Linux: `espeak-ng` | Without one, the video is made with music only |
| Internet | only for `pip install` and the optional AI script | Rendering is fully offline |

## 1. Get the code

```bash
git clone <your-repo-url> propvid
cd propvid
```

Or unzip the submission folder and `cd` into it.

## 2. Create a virtual environment and install dependencies

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

`requirements-dev.txt` installs everything in `requirements.txt` plus `pytest`.

**Linux only:** for narration, install a speech engine:
```bash
sudo apt-get install -y espeak-ng libespeak1
```

## 3. Optional: configure the AI script writer

```bash
cp .env.example .env          # Windows: copy .env.example .env
```

Then set `ANTHROPIC_API_KEY=` in `.env`. Leave it empty to use the offline template writer.
No database, migrations or seed steps are needed. The sample data is in `samples/`.

## 4. Run

**Web app**
```bash
streamlit run app.py
```

Open http://localhost:8501, click **Load sample listing**, then **Generate video**.

**CLI**
```bash
python cli.py samples/sample_property.json -o output/skyline.mp4
python cli.py samples/sample_property.json --horizontal --no-voice -o output/skyline_wide.mp4
python cli.py samples/sample_property.json --ai          # needs ANTHROPIC_API_KEY
```

## 5. Run the tests

```bash
python -m pytest
```

The suite renders a few short videos end to end, so it takes about a minute.

## Common setup errors and fixes

| # | Symptom | Fix |
|---|---|---|
| 1 | `'python' is not recognized` (Windows) | Install Python from python.org with **Add to PATH** ticked, or use `py -3 -m venv .venv` |
| 2 | `Activate.ps1 cannot be loaded because running scripts is disabled` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use `.venv\Scripts\activate.bat` in cmd |
| 3 | `ModuleNotFoundError: No module named 'propvid'` | Run commands from the project root (the folder containing `cli.py`), with the venv activated |
| 4 | `streamlit: command not found` | The venv is not active. Activate it, or run `python -m streamlit run app.py` |
| 5 | Warning *"Text-to-speech is not available on this machine"* | Linux: `sudo apt-get install espeak-ng libespeak1`. Windows: check that a voice is installed under Settings → Time & language → Speech. Or use `--no-voice` |
| 6 | Warning *"AI script requested but ANTHROPIC_API_KEY is not set"* | Create `.env` from `.env.example` and add your key, or skip `--ai`. The template script is used either way |
| 7 | Warning *"AI script unavailable (the API key was rejected)"* | Check the key, or use the template script. The video is still made |
| 8 | `Port 8501 is already in use` | `streamlit run app.py --server.port 8502` |
| 9 | Error *"input file not found"* or *"Image not found and skipped"* | Image paths in the JSON are relative to the JSON file's folder. Check the spelling and extension |
| 10 | The video plays without sound in some players | The audio is AAC in MP4. Use VLC or a browser to confirm, and check the toggles weren't off (`--no-voice --no-music` makes a silent video) |
| 11 | `pip install` fails building `numpy` / `pillow` | Upgrade pip (`python -m pip install --upgrade pip`), and use Python 3.10–3.13 so prebuilt wheels are available |
| 12 | Rendering is slow | Close other heavy apps, or lower the frame rate: `--fps 20` or `PROPVID_FPS=20` |
