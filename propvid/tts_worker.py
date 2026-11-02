"""Stand-alone TTS worker, run in a subprocess by audio.synthesize_narrations().

pyttsx3 drives OS speech engines (SAPI5 / NSSpeechSynthesizer / eSpeak). These engines can hang or
fail when called from Streamlit's worker threads, so the main process keeps them isolated here.

Usage: python tts_worker.py <jobs.json>, where jobs.json = {"rate": int, "jobs": [[text, wav_path], ...]}
"""

import json
import sys


def main(job_file: str) -> int:
    import pyttsx3

    with open(job_file, encoding="utf-8") as fh:
        spec = json.load(fh)
    engine = pyttsx3.init()
    engine.setProperty("rate", spec.get("rate", 165))
    voices = engine.getProperty("voices") or []
    preferred = [v for v in voices if any(k in (v.name or "").lower() for k in ("zira", "female", "samantha"))]
    if preferred:
        engine.setProperty("voice", preferred[0].id)
    for text, path in spec["jobs"]:
        engine.save_to_file(text, path)
    engine.runAndWait()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
