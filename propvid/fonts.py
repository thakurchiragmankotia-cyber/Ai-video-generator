"""Cross-platform font lookup with a fallback chain (DESIGN.md §3)."""

import glob
import os
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

_CANDIDATES = {
    "bold": ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf",
             "Arial Bold.ttf", "Helvetica.ttc"],
    "regular": ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf",
                "Arial.ttf", "Helvetica.ttc"],
}
_FONT_DIRS = [
    os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
    "/Library/Fonts", "/System/Library/Fonts", "/System/Library/Fonts/Supplemental",
    os.path.expanduser("~/Library/Fonts"), "/usr/share/fonts", "/usr/local/share/fonts",
    os.path.expanduser("~/.fonts"),
]
_SPECIAL_CHARS = "₹"


@lru_cache(maxsize=None)
def _font_paths(weight: str) -> tuple[str, ...]:
    """All installed candidate fonts for a weight, in preference order."""
    found = []
    for name in _CANDIDATES[weight]:
        for folder in _FONT_DIRS:
            direct = os.path.join(folder, name)
            matches = [direct] if os.path.isfile(direct) else glob.glob(os.path.join(folder, "**", name), recursive=True)
            if matches:
                found.append(matches[0])
                break
    return tuple(found)


@lru_cache(maxsize=256)
def _truetype(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return None


def _render(font, char: str) -> bytes:
    size = int(getattr(font, "size", 16)) * 2
    img = Image.new("L", (size, size), 0)
    ImageDraw.Draw(img).text((0, 0), char, font=font, fill=255)
    return img.tobytes()


def supports(font, char: str) -> bool:
    """True if the font has a real glyph for `char` (not the empty 'missing glyph' box)."""
    try:
        return _render(font, char) != _render(font, "\U0010FFFD")
    except Exception:  # noqa: BLE001 - any font engine error means "not supported"
        return False


@lru_cache(maxsize=512)
def load_font(weight: str, size: int, text: str = ""):
    """Return a font of the given weight ("bold" | "regular") and pixel size.

    If `text` contains special characters (like ₹), prefer the first candidate font that can draw them.
    """
    size = max(8, int(size))
    fonts = [f for f in (_truetype(p, size) for p in _font_paths(weight)) if f is not None]
    needed = [c for c in _SPECIAL_CHARS if c in text]
    for font in fonts:
        if all(supports(font, c) for c in needed):
            return font
    return fonts[0] if fonts else ImageFont.load_default(size)


def safe_text(text: str, font) -> str:
    """Swap characters the font cannot draw for readable ASCII equivalents."""
    if "₹" in text and not supports(font, "₹"):
        text = text.replace("₹ ", "Rs. ").replace("₹", "Rs. ")
    return text
