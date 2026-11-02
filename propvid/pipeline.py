"""generate_video(): the single entry point used by both the CLI and the web app."""

import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from . import theme
from .audio import SAMPLE_RATE, mix_track, synthesize_narrations, write_wav
from .config import RenderOptions
from .images import load_images
from .models import Script
from .renderer import render_video, timeline
from .script_writer import write_script
from .validation import build_property

ProgressFn = Callable[[float, str], None]

# share of the progress bar given to each stage
_STAGES = {"script": 0.05, "images": 0.10, "audio": 0.20, "render": 1.0}


@dataclass
class VideoResult:
    output_path: Path
    script: Script
    duration: float
    warnings: list[str] = field(default_factory=list)
    has_narration: bool = False
    has_music: bool = False
    vertical: bool = True


def _scene_durations(script: Script, voice) -> list[float]:
    """Each scene lasts its minimum, or long enough for its narration, whichever is longer.

    Narrated scenes are never cut short (that would clip the voice). Silent scenes keep their minimum.
    """
    durations = []
    for scene, clip in zip(script.scenes, voice):
        duration = theme.MIN_DURATION[scene.kind]
        if clip is not None:
            spoken = len(clip) / SAMPLE_RATE
            duration = max(duration, theme.NARRATION_LEAD + spoken + theme.NARRATION_TAIL)
        durations.append(duration)
    return durations


def generate_video(
    data: dict,
    output_path: Path | str,
    options: RenderOptions | None = None,
    base_dir: Path | str | None = None,
    progress: ProgressFn | None = None,
) -> VideoResult:
    """Validate input, write the script, synthesise audio, render and encode the MP4.

    Raises InputError for problems the user must fix. Everything else that can be worked around
    is returned in VideoResult.warnings.
    """
    options = options or RenderOptions()
    report = progress or (lambda fraction, label: None)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report(0.0, "Checking input")
    prop, warnings = build_property(data, base_dir)

    report(_STAGES["script"], "Loading images")
    images, image_warnings = load_images(prop.image_paths)
    warnings += image_warnings

    report(_STAGES["images"], "Writing script" + (" with AI" if options.use_ai else ""))
    script, script_warnings = write_script(prop, len(images), use_ai=options.use_ai)
    warnings += script_warnings

    with tempfile.TemporaryDirectory(prefix="propvid_") as tmp:
        work = Path(tmp)
        voice = [None] * len(script.scenes)
        if options.narration:
            report(_STAGES["images"] + 0.02, "Generating narration")
            voice, voice_warnings = synthesize_narrations([s.narration for s in script.scenes], work)
            warnings += voice_warnings

        for scene, duration in zip(script.scenes, _scene_durations(script, voice)):
            scene.duration = duration
        starts, total = timeline([s.duration for s in script.scenes])

        audio_path = None
        has_voice = any(c is not None for c in voice)
        if has_voice or options.music:
            report(_STAGES["audio"] - 0.03, "Mixing audio")
            clips = [(start + theme.NARRATION_LEAD, clip) for start, clip in zip(starts, voice) if clip is not None]
            audio_path = work / "track.wav"
            write_wav(audio_path, mix_track(total, clips, with_music=options.music))

        def render_progress(fraction: float, label: str) -> None:
            report(_STAGES["audio"] + (1 - _STAGES["audio"]) * fraction * 0.98, label)

        duration = render_video(
            script.scenes, prop, images, options.size, options.fps, output_path,
            audio_path=audio_path, progress=render_progress,
        )

    report(1.0, "Done")
    return VideoResult(
        output_path=output_path, script=script, duration=duration, warnings=warnings,
        has_narration=has_voice, has_music=options.music,
        vertical=options.orientation == "vertical",
    )
