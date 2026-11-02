"""Narration (offline TTS), generated background music, and mixing into one WAV track."""

import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

from . import theme
from .script_writer import speakable

SAMPLE_RATE = 44_100
TTS_RATE_WPM = 175
TTS_TIMEOUT_S = 120
MUSIC_GAIN = 0.22
MUSIC_DUCKED_GAIN = 0.08
VOICE_PEAK = 0.9


# --------------------------------------------------------------------------- WAV I/O

def read_wav(path: Path) -> np.ndarray:
    """Read a PCM WAV as mono float32 at SAMPLE_RATE."""
    with wave.open(str(path), "rb") as wf:
        rate, channels, width = wf.getframerate(), wf.getnchannels(), wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())
    if width == 2:
        data = np.frombuffer(raw, "<i2").astype(np.float32) / 32768.0
    elif width == 1:
        data = (np.frombuffer(raw, np.uint8).astype(np.float32) - 128) / 128.0
    elif width == 4:
        data = np.frombuffer(raw, "<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"unsupported WAV sample width: {width}")
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    if rate != SAMPLE_RATE and len(data):
        n_out = int(len(data) * SAMPLE_RATE / rate)
        data = np.interp(np.linspace(0, len(data) - 1, n_out), np.arange(len(data)), data).astype(np.float32)
    return data


def write_wav(path: Path, samples: np.ndarray, rate: int = SAMPLE_RATE) -> None:
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm.tobytes())


def _trim_silence(samples: np.ndarray, threshold: float = 0.01) -> np.ndarray:
    loud = np.flatnonzero(np.abs(samples) > threshold)
    if not len(loud):
        return samples[:0]
    pad = int(0.05 * SAMPLE_RATE)
    return samples[max(0, loud[0] - pad): loud[-1] + pad]


# --------------------------------------------------------------------------- narration

def synthesize_narrations(texts: list[str], work_dir: Path) -> tuple[list[np.ndarray | None], list[str]]:
    """Speak each text to a clip (None for empty text). On TTS failure every clip is None, with a warning."""
    jobs = []
    for i, text in enumerate(texts):
        if text.strip():
            jobs.append([speakable(text), str(work_dir / f"voice_{i}.wav")])
    if not jobs:
        return [None] * len(texts), []

    job_file = work_dir / "tts_jobs.json"
    job_file.write_text(json.dumps({"rate": TTS_RATE_WPM, "jobs": jobs}), encoding="utf-8")
    worker = Path(__file__).with_name("tts_worker.py")
    try:
        result = subprocess.run(
            [sys.executable, str(worker), str(job_file)],
            capture_output=True, text=True, timeout=TTS_TIMEOUT_S,
        )
        failed = result.returncode != 0
    except (subprocess.TimeoutExpired, OSError):
        failed = True
    if failed:
        return [None] * len(texts), ["Text-to-speech is not available on this machine: the video has music only."]

    clips: list[np.ndarray | None] = []
    warnings: list[str] = []
    for i, text in enumerate(texts):
        path = work_dir / f"voice_{i}.wav"
        if not text.strip():
            clips.append(None)
            continue
        try:
            clip = _trim_silence(read_wav(path))
        except (OSError, EOFError, wave.Error, ValueError):
            clip = None
        if clip is None or not len(clip):
            warnings.append(f"Narration for scene {i + 1} could not be generated.")
            clip = None
        else:
            clip = clip / max(np.abs(clip).max(), 1e-6) * VOICE_PEAK
        clips.append(clip)
    return clips, warnings


# --------------------------------------------------------------------------- music

# A slow I - vi - IV - V progression in C major (note frequencies in Hz), 4 s per chord
_CHORDS = [
    [130.81, 196.00, 261.63, 329.63, 392.00],   # Cmaj
    [110.00, 164.81, 220.00, 261.63, 329.63],   # Am
    [87.31, 174.61, 220.00, 261.63, 349.23],    # Fmaj
    [98.00, 146.83, 196.00, 246.94, 293.66],    # Gmaj
]
_CHORD_SECONDS = 4.0


def generate_music(duration: float, rate: int = SAMPLE_RATE) -> np.ndarray:
    """Soft ambient pad with a gentle arpeggio. Generated from sine waves, so it is royalty-free."""
    n = int(duration * rate)
    t = np.arange(n, dtype=np.float32) / rate
    out = np.zeros(n, np.float32)
    chord_n = int(_CHORD_SECONDS * rate)
    xfade = int(0.8 * rate)

    for start in range(0, n, chord_n):
        chord = _CHORDS[(start // chord_n) % len(_CHORDS)]
        end = min(n, start + chord_n + xfade)
        seg_t = t[start:end]
        local = seg_t - seg_t[0]
        env = np.minimum(1.0, local / 0.8) * np.minimum(1.0, (end - start) / rate - local) / 1.0
        env = np.clip(env, 0.0, 1.0)
        pad = np.zeros(end - start, np.float32)
        for k, f in enumerate(chord):
            # two slightly detuned sines per note give a warm chorus effect
            amp = 0.16 if k else 0.22
            pad += amp * (np.sin(2 * np.pi * f * seg_t) + 0.6 * np.sin(2 * np.pi * f * 1.003 * seg_t + k))
        out[start:end] += pad * env

        # arpeggio: plucked upper chord tones on every half second
        for j in range(int(_CHORD_SECONDS * 2)):
            s = start + int(j * 0.5 * rate)
            if s >= n:
                break
            note = chord[2 + j % 3] * 2
            length = min(int(1.2 * rate), n - s)
            lt = np.arange(length, dtype=np.float32) / rate
            pluck = np.sin(2 * np.pi * note * lt) * np.exp(-lt * 3.5) * 0.12
            out[s:s + length] += pluck

    out /= max(np.abs(out).max(), 1e-6)
    fade_in, fade_out = int(1.5 * rate), int(2.0 * rate)
    out[:fade_in] *= np.linspace(0, 1, min(fade_in, n))[: len(out[:fade_in])]
    if n > fade_out:
        out[-fade_out:] *= np.linspace(1, 0, fade_out)
    return out


# --------------------------------------------------------------------------- mixing

def _smooth(mask: np.ndarray, seconds: float) -> np.ndarray:
    k = max(1, int(seconds * SAMPLE_RATE))
    kernel = np.ones(k, np.float32) / k
    return np.convolve(mask, kernel, mode="same")


def mix_track(duration: float, voice_clips: list[tuple[float, np.ndarray]], with_music: bool) -> np.ndarray:
    """Place voice clips at their start times over the music. The music is ducked while someone speaks."""
    n = int(duration * SAMPLE_RATE)
    voice = np.zeros(n, np.float32)
    for start, clip in voice_clips:
        s = int(start * SAMPLE_RATE)
        e = min(n, s + len(clip))
        if e > s:
            voice[s:e] += clip[: e - s]

    track = voice.copy()
    if with_music:
        speaking = _smooth((np.abs(voice) > 0.02).astype(np.float32), 0.25)
        speaking = _smooth(np.clip(speaking * 4, 0, 1), 0.3)
        gain = MUSIC_GAIN - (MUSIC_GAIN - MUSIC_DUCKED_GAIN) * np.clip(speaking, 0, 1)
        track += generate_music(duration) * gain

    fade = int(theme.AUDIO_FADE_OUT * SAMPLE_RATE)
    if n > fade:
        track[-fade:] *= np.linspace(1, 0, fade)
    peak = np.abs(track).max() if n else 0
    if peak > 0.98:
        track *= 0.98 / peak
    return track
