import subprocess

import imageio_ffmpeg
import numpy as np
import pytest

from propvid.audio import generate_music, mix_track
from propvid.config import RenderOptions
from propvid.errors import InputError
from propvid.models import PropertyInput, Scene
from propvid.overlays import fit_text, scene_layers, wrap_text
from propvid.fonts import load_font
from propvid.pipeline import generate_video
from propvid.renderer import timeline


def _probe(path) -> str:
    result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(path)],
                            capture_output=True, text=True)
    return result.stderr


def test_timeline_overlaps_by_crossfade():
    starts, total = timeline([4.0, 5.0, 3.0], fade=0.5)
    assert starts == [0.0, 3.5, 8.0]
    assert total == pytest.approx(11.0)


def test_wrap_text_respects_width():
    font = load_font("bold", 40)
    lines = wrap_text("Modular kitchen with built-in chimney and breakfast counter", font, 300)
    assert len(lines) > 1
    assert all(font.getlength(line) <= 300 for line in lines)


def test_fit_text_truncates_extreme_text():
    _, lines = fit_text("word " * 80, "bold", 52, 400, 3)
    assert len(lines) == 3 and lines[-1].endswith("…")


@pytest.mark.parametrize("kind", ["title", "feature", "gallery", "cta"])
def test_scene_layers_are_frame_sized(kind):
    prop = PropertyInput(name="Skyline Residency", location="Whitefield", price="₹85 Lakh", contact="Call 123")
    static, text = scene_layers(Scene(kind, "Caption text", label="LABEL"), prop, (360, 640), 0, 3)
    assert static.size == text.size == (360, 640)
    assert text.getbbox() is not None  # something was drawn


def test_music_is_normalised_and_mix_is_safe():
    music = generate_music(3.0)
    assert len(music) == 3 * 44_100 and np.abs(music).max() <= 1.0
    track = mix_track(3.0, [(0.5, np.ones(44_100, np.float32))], with_music=True)
    assert np.abs(track).max() <= 0.98 + 1e-6


def test_end_to_end_silent_render(listing, make_images, tmp_path):
    listing["images"] = [str(p) for p in make_images(4)]
    out = tmp_path / "out.mp4"
    options = RenderOptions(narration=False, music=False, fps=12)
    result = generate_video(listing, out, options)
    assert out.exists() and out.stat().st_size > 10_000
    assert 20 <= result.duration <= 40
    info = _probe(out)
    assert "Video: h264" in info and "720x1280" in info


def test_end_to_end_with_music_has_audio(listing, make_images, tmp_path):
    listing["images"] = [str(p) for p in make_images(4)]
    out = tmp_path / "music.mp4"
    generate_video(listing, out, RenderOptions(orientation="horizontal", narration=False, music=True, fps=12))
    info = _probe(out)
    assert "Audio: aac" in info and "1280x720" in info


def test_end_to_end_without_images_uses_placeholders(tmp_path):
    out = tmp_path / "plain.mp4"
    result = generate_video({"name": "Plot 7", "features": ["Corner plot"]}, out,
                            RenderOptions(narration=False, music=False, fps=12))
    assert out.exists()
    assert any("placeholder" in w for w in result.warnings)


def test_invalid_input_raises_before_rendering(tmp_path):
    with pytest.raises(InputError):
        generate_video({"price": "₹1 Cr"}, tmp_path / "x.mp4", RenderOptions(narration=False, music=False))
    assert not (tmp_path / "x.mp4").exists()
