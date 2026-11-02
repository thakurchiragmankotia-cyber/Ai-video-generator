"""Turn scenes into frames and encode them with ffmpeg (bundled by imageio-ffmpeg).

Timeline: scenes overlap by theme.CROSSFADE seconds, and during an overlap the two frames are blended.
Each scene's photo is pre-scaled once. Every frame then crops a moving window (Ken Burns) and
composites the scene's pre-drawn overlay layers on top.
"""

import math
from collections.abc import Callable
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image

from . import theme
from .images import cover_fit, placeholder
from .models import PropertyInput, Scene
from .overlays import scene_layers

OVERSCAN = 1.0 + theme.KEN_BURNS_ZOOM + 0.04   # extra source pixels needed for zoom + pan
MOTIONS = ["zoom_in", "pan_right", "zoom_out", "pan_left"]

ProgressFn = Callable[[float, str], None]


def timeline(durations: list[float], fade: float = theme.CROSSFADE) -> tuple[list[float], float]:
    """Start time of each scene and the total length, with neighbouring scenes overlapping by `fade`."""
    starts, t = [], 0.0
    for i, d in enumerate(durations):
        starts.append(t)
        t += d - (fade if i < len(durations) - 1 else 0.0)
    return starts, t


def _ease_out(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


class SceneClip:
    """Renders one scene at any local time t (seconds since the scene started)."""

    def __init__(self, scene: Scene, image: Image.Image | None, size: tuple[int, int], motion: str,
                 layers: tuple[Image.Image, Image.Image], variant: int):
        self.scene = scene
        self.size = size
        self.motion = motion
        w, h = size
        big = (math.ceil(w * OVERSCAN), math.ceil(h * OVERSCAN))
        self.big = cover_fit(image, big) if image is not None else placeholder(big, variant)
        self.static, self.text = layers
        self.text_alpha = self.text.getchannel("A")

    def _crop_box(self, p: float) -> tuple[float, float, float, float]:
        bw, bh = self.big.size
        if self.motion in ("zoom_in", "zoom_out"):
            e = p if self.motion == "zoom_in" else 1 - p
            zoom = 1.0 + theme.KEN_BURNS_ZOOM * e
            cw, ch = bw / zoom, bh / zoom
            x0, y0 = (bw - cw) / 2, (bh - ch) * 0.45
        else:
            zoom = 1.0 + theme.KEN_BURNS_ZOOM * 0.6
            cw, ch = bw / zoom, bh / zoom
            e = p if self.motion == "pan_right" else 1 - p
            x0, y0 = (bw - cw) * e, (bh - ch) / 2
        return x0, y0, x0 + cw, y0 + ch

    def frame(self, t: float) -> Image.Image:
        p = min(max(t / max(self.scene.duration, 1e-6), 0.0), 1.0)
        base = self.big.resize(self.size, Image.BILINEAR, box=self._crop_box(p)).convert("RGBA")
        base.alpha_composite(self.static)

        a = _ease_out((t - theme.TEXT_DELAY) / theme.TEXT_ANIM)
        if a >= 1.0:
            base.alpha_composite(self.text)
        elif a > 0.0:
            layer = self.text.copy()
            layer.putalpha(self.text_alpha.point(lambda v: int(v * a)))
            dy = round(theme.TEXT_SLIDE_PX * (1 - a))
            w, h = self.size
            base.alpha_composite(layer.crop((0, 0, w, h - dy)), (0, dy))
        return base.convert("RGB")


def build_clips(scenes: list[Scene], prop: PropertyInput, images: list[Image.Image],
                size: tuple[int, int]) -> list[SceneClip]:
    total_features = sum(1 for s in scenes if s.kind == "feature")
    clips, feature_i = [], 0
    for i, scene in enumerate(scenes):
        layers = scene_layers(scene, prop, size, feature_i, total_features)
        if scene.kind == "feature":
            feature_i += 1
        image = images[scene.image_index] if scene.image_index is not None and images else None
        clips.append(SceneClip(scene, image, size, MOTIONS[i % len(MOTIONS)], layers, i))
    return clips


def render_video(scenes: list[Scene], prop: PropertyInput, images: list[Image.Image],
                 size: tuple[int, int], fps: int, out_path: Path, audio_path: Path | None = None,
                 progress: ProgressFn | None = None) -> float:
    """Encode the video to `out_path` and return its duration in seconds."""
    clips = build_clips(scenes, prop, images, size)
    starts, total = timeline([s.duration for s in scenes])
    n_frames = max(1, round(total * fps))

    output_params = ["-crf", "20", "-preset", "medium", "-movflags", "+faststart"]
    if audio_path is not None:
        output_params += ["-b:a", "160k", "-shortest"]
    writer = imageio_ffmpeg.write_frames(
        str(out_path), size, fps=fps, codec="libx264", quality=None, pix_fmt_out="yuv420p",
        macro_block_size=8, output_params=output_params, ffmpeg_log_level="error",
        audio_path=str(audio_path) if audio_path else None, audio_codec="aac" if audio_path else None,
    )
    writer.send(None)
    try:
        current = 0
        for n in range(n_frames):
            t = n / fps
            while current + 1 < len(clips) and t >= starts[current + 1] + theme.CROSSFADE:
                current += 1
            frame = clips[current].frame(t - starts[current])
            nxt = current + 1
            if nxt < len(clips) and t >= starts[nxt]:
                # inside a crossfade: blend towards the next scene
                alpha = (t - starts[nxt]) / theme.CROSSFADE
                frame = Image.blend(frame, clips[nxt].frame(t - starts[nxt]), min(max(alpha, 0.0), 1.0))
            writer.send(np.asarray(frame, dtype=np.uint8))
            if progress and n % max(1, fps // 2) == 0:
                progress(n / n_frames, f"Rendering frames ({n}/{n_frames})")
    finally:
        writer.close()
    return total
