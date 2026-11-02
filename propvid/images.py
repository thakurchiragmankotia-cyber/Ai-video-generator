"""Load, verify and fit images. Broken images become warnings, never crashes."""

import warnings as _warnings
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from . import theme
from .validation import MAX_IMAGES, MIN_IMAGES

MAX_SOURCE_SIDE = 2400   # downscale huge photos early to keep memory and render time low
LOW_RES_SIDE = 500

Image.MAX_IMAGE_PIXELS = 120_000_000


def load_images(paths: list[Path]) -> tuple[list[Image.Image], list[str]]:
    """Open each image, fix EXIF rotation and convert to RGB. Returns (images, warnings)."""
    images, warnings = [], []
    for path in paths[:MAX_IMAGES]:
        try:
            with _warnings.catch_warnings():
                _warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(path) as im:
                    im.load()
                    img = ImageOps.exif_transpose(im).convert("RGB")
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
            warnings.append(f"Skipped {Path(path).name}: the file is not a readable image.")
            continue
        except (Image.DecompressionBombError, Image.DecompressionBombWarning):
            warnings.append(f"Skipped {Path(path).name}: the image is too large.")
            continue
        if min(img.size) < LOW_RES_SIDE:
            warnings.append(f"{Path(path).name} is low resolution ({img.width}x{img.height}) and may look blurry.")
        img.thumbnail((MAX_SOURCE_SIDE, MAX_SOURCE_SIDE), Image.LANCZOS)
        images.append(img)

    if not images:
        warnings.append("No usable images: branded placeholder backgrounds are used instead.")
    elif len(images) < MIN_IMAGES:
        warnings.append(
            f"Only {len(images)} usable image(s); {MIN_IMAGES}-{MAX_IMAGES} are recommended. Images are reused across scenes."
        )
    return images, warnings


def cover_fit(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Scale to fill `size` completely and centre-crop the overflow (no bars, no stretching)."""
    return ImageOps.fit(img, size, method=Image.LANCZOS, centering=(0.5, 0.45))


def placeholder(size: tuple[int, int], variant: int = 0) -> Image.Image:
    """Diagonal teal gradient used when a scene has no photo."""
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = (xx / max(w, 1) * 0.35 + yy / max(h, 1) * 0.65)
    if variant % 2:
        t = 1 - t
    start, end = np.array(theme.PRIMARY, np.float32), np.array(theme.PRIMARY_DARK, np.float32)
    arr = start + (end - start) * t[..., None]
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGB")
