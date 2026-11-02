"""Design tokens from DESIGN.md. Every colour, size and timing used for rendering lives here."""

# Colours (RGB / RGBA)
PRIMARY = (15, 61, 62)          # #0F3D3E deep teal
PRIMARY_DARK = (8, 34, 35)      # placeholder gradient end
SECONDARY = (200, 164, 92)      # #C8A45C muted gold
TEXT = (255, 255, 255)
TEXT_MUTED = (217, 212, 199)    # #D9D4C7
SCRIM_MAX_ALPHA = 200           # ~78% black at the very bottom
SHADOW_ALPHA = 140              # ~55% black text shadow
CTA_CARD_ALPHA = 235            # ~92% opaque teal card

# Typography sizes in px at the 720x1280 reference frame
TITLE_SIZE = 64
CAPTION_SIZE = 52
SUBTITLE_SIZE = 34
PRICE_SIZE = 38
LABEL_SIZE = 24
CTA_HEADING_SIZE = 56
CTA_CONTACT_SIZE = 36
LINE_HEIGHT_TIGHT = 1.15
LINE_HEIGHT = 1.2
LINE_HEIGHT_LOOSE = 1.3
MAX_CAPTION_LINES = 3

# Spacing / shape
MARGIN_VERTICAL = 48
MARGIN_HORIZONTAL = 40
GAP_S = 12
GAP_M = 16
GAP_L = 24
RADIUS_CARD = 16
RADIUS_LABEL = 8
SHADOW_OFFSET = 2
SHADOW_BLUR = 3                 # Gaussian radius; ~6 px visual blur

# Motion and timing (seconds)
CROSSFADE = 0.6
TEXT_DELAY = 0.3
TEXT_ANIM = 0.6
TEXT_SLIDE_PX = 24
KEN_BURNS_ZOOM = 0.08
AUDIO_FADE_OUT = 0.8
NARRATION_LEAD = 0.4            # voice starts this long after a scene begins
NARRATION_TAIL = 0.8            # silence kept after the voice before the next scene

MIN_DURATION = {"title": 4.0, "feature": 4.0, "gallery": 3.5, "cta": 5.0}


def type_scale(width: int, height: int) -> float:
    """Font scale relative to the 720x1280 reference frame (see DESIGN.md §3)."""
    return min(width / 720, height / 1280 * 1.6)
