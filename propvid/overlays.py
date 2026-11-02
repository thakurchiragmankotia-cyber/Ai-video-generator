"""Draw the text overlays for each scene with Pillow (layouts in DESIGN.md §5).

Each scene gets two RGBA layers the size of the frame:
- static: the scrim (or the CTA darkening), visible for the whole scene
- text: captions, labels, price tag, progress dots. The renderer fades and slides this layer in.
"""

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import theme
from .fonts import load_font, safe_text
from .models import PropertyInput, Scene

PAD = 10  # transparent padding around text images so the blurred shadow is not clipped


@dataclass
class Layout:
    width: int
    height: int
    scale: float
    margin: int
    text_width: int
    vertical: bool

    def px(self, value: float) -> int:
        return max(1, round(value * self.scale))


def layout_for(size: tuple[int, int]) -> Layout:
    w, h = size
    vertical = h >= w
    scale = theme.type_scale(w, h)
    margin = round((theme.MARGIN_VERTICAL if vertical else theme.MARGIN_HORIZONTAL) * min(scale, 1.0))
    text_width = w - 2 * margin if vertical else int(w * 0.62)
    return Layout(w, h, scale, margin, text_width, vertical)


# --------------------------------------------------------------------------- text primitives

def wrap_text(text: str, font, max_width: float) -> list[str]:
    """Greedy word wrap. Words wider than the line are broken by character."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if font.getlength(trial) <= max_width:
            current = trial
            continue
        if current:
            lines.append(current)
        while font.getlength(word) > max_width and len(word) > 1:
            cut = len(word)
            while cut > 1 and font.getlength(word[:cut]) > max_width:
                cut -= 1
            lines.append(word[:cut])
            word = word[cut:]
        current = word
    if current:
        lines.append(current)
    return lines or [""]


def fit_text(text: str, weight: str, size: int, max_width: int, max_lines: int):
    """Shrink the font in 10% steps until the text fits in `max_lines`. Truncate as a last resort."""
    min_size = size * 0.6
    while True:
        font = load_font(weight, size, text)
        text_ok = safe_text(text, font)
        lines = wrap_text(text_ok, font, max_width)
        if len(lines) <= max_lines or size * 0.9 < min_size:
            break
        size = int(size * 0.9)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and font.getlength(last + "…") > max_width:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    return font, lines


def text_image(lines: list[str], font, color, line_height: float, align: str = "left",
               box_width: int | None = None) -> Image.Image:
    """Render lines with a soft drop shadow. The result has PAD px of transparent margin."""
    widths = [font.getlength(line) for line in lines]
    inner_w = int(box_width or max(widths) + 1)
    line_px = round(font.size * line_height)
    inner_h = line_px * (len(lines) - 1) + round(font.size * 1.25)
    w, h = inner_w + 2 * PAD, inner_h + 2 * PAD

    shadow = Image.new("L", (w, h), 0)
    text = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ds, dt = ImageDraw.Draw(shadow), ImageDraw.Draw(text)
    off = theme.SHADOW_OFFSET
    for i, line in enumerate(lines):
        x = PAD + (0 if align == "left" else (inner_w - widths[i]) / 2)
        y = PAD + i * line_px
        ds.text((x + off, y + off), line, font=font, fill=theme.SHADOW_ALPHA)
        dt.text((x, y), line, font=font, fill=color)
    shadow = shadow.filter(ImageFilter.GaussianBlur(theme.SHADOW_BLUR))

    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.putalpha(shadow)
    out.alpha_composite(text)
    return out


def label_image(text: str, lay: Layout) -> Image.Image:
    """Small uppercase letter-spaced label with a gold accent bar on its left."""
    font = load_font("bold", lay.px(theme.LABEL_SIZE), text)
    text = safe_text(text.upper(), font)
    spacing = lay.px(2)
    bar_w, gap = lay.px(4), lay.px(10)
    char_w = [font.getlength(c) for c in text]
    width = int(bar_w + gap + sum(char_w) + spacing * max(len(text) - 1, 0)) + 1
    height = round(font.size * 1.25)
    img = Image.new("RGBA", (width + 2 * PAD, height + 2 * PAD), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([PAD, PAD, PAD + bar_w, PAD + height - lay.px(4)],
                        radius=bar_w // 2, fill=theme.SECONDARY)
    x = PAD + bar_w + gap
    for c, cw in zip(text, char_w):
        # one-pixel dark outline instead of a blurred shadow keeps small text crisp
        d.text((x, PAD), c, font=font, fill=theme.TEXT_MUTED, stroke_width=1, stroke_fill=(0, 0, 0, 120))
        x += cw + spacing
    return img


def pill_image(text: str, lay: Layout, size: int, fill=theme.SECONDARY, color=theme.PRIMARY) -> Image.Image:
    font = load_font("bold", lay.px(size), text)
    text = safe_text(text, font)
    pad_x, pad_y = lay.px(18), lay.px(10)
    tw = font.getlength(text)
    th = round(font.size * 1.2)
    w, h = int(tw + 2 * pad_x), th + 2 * pad_y
    img = Image.new("RGBA", (w + 2 * PAD, h + 2 * PAD), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([PAD, PAD, PAD + w, PAD + h], radius=lay.px(theme.RADIUS_CARD), fill=fill)
    d.text((PAD + pad_x, PAD + pad_y - round(font.size * 0.05)), text, font=font, fill=color)
    return img


def _stack(canvas: Image.Image, blocks: list[Image.Image], x: int, bottom: int, gap: int) -> None:
    """Place blocks top-to-bottom so the last block's bottom edge sits at `bottom`."""
    total = sum(b.height - 2 * PAD for b in blocks) + gap * (len(blocks) - 1)
    y = bottom - total
    for block in blocks:
        canvas.alpha_composite(block, (max(0, x - PAD), max(0, y - PAD)))
        y += block.height - 2 * PAD + gap


# --------------------------------------------------------------------------- static layers

def scrim(size: tuple[int, int], fraction: float) -> Image.Image:
    """Transparent-to-black gradient over the bottom `fraction` of the frame."""
    w, h = size
    start = int(h * (1 - fraction))
    alpha = np.zeros(h, np.float32)
    t = np.linspace(0, 1, h - start, dtype=np.float32)
    alpha[start:] = (t ** 1.6) * theme.SCRIM_MAX_ALPHA
    layer = np.zeros((h, w, 4), np.uint8)
    layer[..., 3] = alpha[:, None].astype(np.uint8)
    return Image.fromarray(layer, "RGBA")


def darken(size: tuple[int, int], alpha: int = 115) -> Image.Image:
    return Image.new("RGBA", size, (0, 0, 0, alpha))


# --------------------------------------------------------------------------- scene layouts

def _progress_dots(canvas: Image.Image, lay: Layout, index: int, total: int) -> None:
    if total < 2:
        return
    d = ImageDraw.Draw(canvas)
    r, gap = lay.px(6), lay.px(10)
    y = lay.margin + r
    for i in range(total):
        x = lay.margin + r + i * (2 * r + gap)
        fill = theme.SECONDARY + (255,) if i <= index else (255, 255, 255, 110)
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def _title_layers(scene: Scene, prop: PropertyInput, lay: Layout) -> list[Image.Image]:
    blocks = []
    if scene.label:
        blocks.append(label_image(scene.label, lay))
    font, lines = fit_text(scene.caption, "bold", lay.px(theme.TITLE_SIZE), lay.text_width, theme.MAX_CAPTION_LINES)
    blocks.append(text_image(lines, font, theme.TEXT, theme.LINE_HEIGHT_TIGHT))
    if prop.location:
        font, lines = fit_text(prop.location, "regular", lay.px(theme.SUBTITLE_SIZE), lay.text_width, 2)
        blocks.append(text_image(lines, font, theme.TEXT_MUTED, theme.LINE_HEIGHT_LOOSE))
    if prop.price:
        blocks.append(pill_image(prop.price, lay, theme.PRICE_SIZE))
    return blocks


def _caption_layers(scene: Scene, lay: Layout, size: int) -> list[Image.Image]:
    blocks = [label_image(scene.label, lay)] if scene.label else []
    font, lines = fit_text(scene.caption, "bold", lay.px(size), lay.text_width, theme.MAX_CAPTION_LINES)
    blocks.append(text_image(lines, font, theme.TEXT, theme.LINE_HEIGHT))
    return blocks


def _cta_card(scene: Scene, prop: PropertyInput, lay: Layout) -> Image.Image:
    card_w = lay.width - 2 * lay.margin if lay.vertical else int(lay.width * 0.56)
    inner = card_w - 2 * lay.px(32)
    parts = []
    if scene.label:
        f, lines = fit_text(scene.label, "bold", lay.px(theme.LABEL_SIZE), inner, 1)
        parts.append(text_image(lines, f, theme.SECONDARY, 1.1, "center", inner))
    f, lines = fit_text(scene.caption, "bold", lay.px(theme.CTA_HEADING_SIZE), inner, theme.MAX_CAPTION_LINES)
    parts.append(text_image(lines, f, theme.TEXT, theme.LINE_HEIGHT_TIGHT, "center", inner))
    if prop.contact:
        f, lines = fit_text(prop.contact, "regular", lay.px(theme.CTA_CONTACT_SIZE), inner, 2)
        parts.append(text_image(lines, f, theme.TEXT, theme.LINE_HEIGHT_LOOSE, "center", inner))
    if prop.price:
        parts.append(pill_image(prop.price, lay, theme.PRICE_SIZE))

    gap = lay.px(theme.GAP_L)
    pad_y = lay.px(36)
    content_h = sum(p.height - 2 * PAD for p in parts) + gap * (len(parts) - 1)
    card_h = content_h + 2 * pad_y
    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle(
        [0, 0, card_w - 1, card_h - 1], radius=lay.px(theme.RADIUS_CARD),
        fill=theme.PRIMARY + (theme.CTA_CARD_ALPHA,), outline=theme.SECONDARY + (255,), width=lay.px(2),
    )
    y = pad_y
    for p in parts:
        x = (card_w - (p.width - 2 * PAD)) // 2
        card.alpha_composite(p, (max(0, x - PAD), max(0, y - PAD)))
        y += p.height - 2 * PAD + gap
    return card


def scene_layers(scene: Scene, prop: PropertyInput, size: tuple[int, int],
                 feature_index: int = 0, feature_total: int = 0) -> tuple[Image.Image, Image.Image]:
    """Return (static_layer, text_layer) for one scene."""
    lay = layout_for(size)
    text = Image.new("RGBA", size, (0, 0, 0, 0))
    bottom = lay.height - lay.margin - (lay.px(24) if lay.vertical else 0)

    if scene.kind == "cta":
        static = darken(size)
        card = _cta_card(scene, prop, lay)
        text.alpha_composite(card, ((lay.width - card.width) // 2, max(0, (lay.height - card.height) // 2)))
        return static, text

    static = scrim(size, 0.55 if lay.vertical else 0.65)
    if scene.kind == "title":
        blocks = _title_layers(scene, prop, lay)
    elif scene.kind == "feature":
        blocks = _caption_layers(scene, lay, theme.CAPTION_SIZE)
        _progress_dots(text, lay, feature_index, feature_total)
    else:  # gallery
        blocks = _caption_layers(scene, lay, round(theme.CAPTION_SIZE * 0.8))
    _stack(text, blocks, lay.margin, bottom, lay.px(theme.GAP_M))
    return static, text
