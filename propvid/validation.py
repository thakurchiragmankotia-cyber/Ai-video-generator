"""Turn raw input (form values or JSON) into a PropertyInput plus non-blocking warnings."""

import re
from pathlib import Path
from typing import Any

from .errors import InputError
from .models import PropertyInput

MIN_IMAGES = 4
MAX_IMAGES = 8
MAX_FEATURES = 5
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# field name -> max length; longer values cannot be laid out readably on a phone screen
FIELD_LIMITS = {
    "name": 80,
    "location": 90,
    "price": 40,
    "property_type": 40,
    "cta": 90,
    "contact": 90,
}
MAX_FEATURE_LENGTH = 80

_BULLET = re.compile(r"^\s*(?:[-*•·–]|\d+[.)])\s*")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def parse_features(raw: Any) -> list[str]:
    """Accept a list or a block of text (one feature per line, or comma-separated on one line)."""
    if raw is None:
        return []
    if isinstance(raw, str):
        lines = raw.splitlines()
        if len(lines) == 1 and "," in raw:
            lines = raw.split(",")
        items = lines
    elif isinstance(raw, (list, tuple)):
        items = [str(x) for x in raw]
    else:
        raise InputError("Features must be a list or text with one feature per line.")

    features, seen = [], set()
    for item in items:
        text = _clean(_BULLET.sub("", str(item))).rstrip(".;")
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            features.append(text)
    return features


def _resolve_images(raw: Any, base_dir: Path | None, warnings: list[str]) -> list[Path]:
    if raw is None:
        return []
    if isinstance(raw, (str, Path)):
        raw = [raw]
    paths = []
    for item in raw:
        path = Path(str(item)).expanduser()
        if not path.is_absolute() and base_dir is not None:
            path = base_dir / path
        if not path.exists():
            warnings.append(f"Image not found and skipped: {item}")
        elif path.suffix.lower() not in IMAGE_EXTENSIONS:
            warnings.append(
                f"Unsupported image type skipped: {path.name} (use JPG, PNG, WebP or BMP)"
            )
        else:
            paths.append(path)
    return paths


def build_property(data: dict, base_dir: Path | str | None = None) -> tuple[PropertyInput, list[str]]:
    """Validate raw input. Raises InputError for blocking problems, returns warnings otherwise."""
    if not isinstance(data, dict):
        raise InputError("Input must be an object with property fields (name, location, price, ...).")

    base = Path(base_dir) if base_dir else None
    warnings: list[str] = []
    values = {key: _clean(data.get(key)) for key in FIELD_LIMITS}
    # accept a few common alternative keys from hand-written JSON
    values["property_type"] = values["property_type"] or _clean(data.get("type"))
    values["cta"] = values["cta"] or _clean(data.get("cta_text"))

    if not values["name"]:
        raise InputError("Property name is required, e.g. \"Skyline Residency\".")
    for key, limit in FIELD_LIMITS.items():
        if len(values[key]) > limit:
            label = key.replace("_", " ")
            raise InputError(f"The {label} is too long ({len(values[key])} characters, max {limit}). Please shorten it.")

    features = parse_features(data.get("features"))
    too_long = [f for f in features if len(f) > MAX_FEATURE_LENGTH]
    if too_long:
        raise InputError(
            f"Feature is too long for a caption (max {MAX_FEATURE_LENGTH} characters): \"{too_long[0][:40]}...\""
        )
    if not features:
        warnings.append("No key features given: the video will show photos without feature captions.")
    elif len(features) > MAX_FEATURES:
        warnings.append(f"{len(features)} features given: only the first {MAX_FEATURES} are shown.")
        features = features[:MAX_FEATURES]

    if not values["price"]:
        warnings.append("No price given: the price tag is left out.")
    if not values["location"]:
        warnings.append("No location given: the location line is left out.")
    if not values["cta"] and not values["contact"]:
        warnings.append("No contact or call-to-action given: the end card shows a generic enquiry prompt.")

    images = _resolve_images(data.get("images"), base, warnings)
    if len(images) > MAX_IMAGES:
        warnings.append(f"{len(images)} images given: only the first {MAX_IMAGES} are used.")
        images = images[:MAX_IMAGES]

    prop = PropertyInput(
        name=values["name"],
        location=values["location"],
        price=values["price"],
        property_type=values["property_type"],
        features=features,
        cta=values["cta"],
        contact=values["contact"],
        image_paths=images,
    )
    return prop, warnings
