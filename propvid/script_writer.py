"""Build the scene list and write captions and narration.

Two writers fill the same fixed scene structure:
- template_script(): deterministic and offline, and uses only input fields.
- ai_script(): asks Claude for livelier wording. Its output must pass fact_check(),
  otherwise the template script is used instead.
"""

import json
import re

from . import config
from .models import PropertyInput, Scene, Script

MAX_SCENES = 8
MIN_FEATURE_SCENES = 3
MAX_CAPTION_CHARS = 60
MAX_NARRATION_CHARS = 220
GENERIC_CTA = "Enquire today to book a visit"

_CONTACT_VERBS = r"(call|whatsapp|email|e-mail|mail|contact|phone|ring|text|sms|message|reach|visit|dm|write)\b"
# Features are noun phrases ("Modular kitchen with chimney"), so they are read as ad-style lines
# rather than forced into sentences that would need articles we cannot reliably guess.
_FEATURE_LEADS = ["{F}.", "{F}.", "Plus, {f}.", "{F}.", "And finally, {f}."]


# --------------------------------------------------------------------------- helpers

def _lower_first(text: str) -> str:
    """Lowercase the first letter unless the first word looks like an acronym (BHK, RERA)."""
    if len(text) > 1 and text[0].isupper() and text[1].islower():
        return text[0].lower() + text[1:]
    return text


def _sentence(text: str) -> str:
    text = text.strip()
    return text if not text or text[-1] in ".!?" else text + "."


def speakable(text: str) -> str:
    """Rewrite symbols and abbreviations so offline TTS pronounces them sensibly."""
    out = text.replace("₹", " rupees ").replace("&", " and ").replace("@", " at ")
    out = re.sub(r"\bsq\.?\s?ft\b|\bsqft\b", "square feet", out, flags=re.I)
    out = re.sub(r"\bBHK\b", "B H K", out)
    out = re.sub(r"\bCr\b\.?", "crore", out)
    out = re.sub(r"(?<=\d)\s?L\b", " lakh", out)
    out = re.sub(r"\bnr\.?\b", "near", out, flags=re.I)
    # long digit runs (phone numbers) are read digit by digit, not as one huge number
    out = re.sub(r"\+?\d[\d\s-]{7,}\d", lambda m: " ".join(re.sub(r"\D", "", m.group())), out)
    out = re.sub(r"\s+", " ", out).strip()
    # "rupees 85 lakh" -> "85 lakh rupees"
    out = re.sub(r"rupees ([\d.,]+(?: (?:lakhs?|crores?|thousand|million))?)", r"\1 rupees", out, flags=re.I)
    return out


def _assign_images(scenes: list[Scene], image_count: int) -> None:
    """Give each scene an image. The title gets the first and the CTA the last when there are enough."""
    if image_count == 0:
        return
    for i, scene in enumerate(scenes):
        scene.image_index = i % image_count
    if image_count >= len(scenes):
        scenes[-1].image_index = image_count - 1


def scene_plan(prop: PropertyInput, image_count: int) -> list[Scene]:
    """Fixed structure: title, 3-5 feature scenes (gallery scenes when features are few), CTA.

    Extra photos beyond the feature scenes become short gallery scenes, so every photo is shown.
    """
    scenes = [Scene(kind="title", caption=prop.name, label=prop.property_type.upper())]
    total = len(prop.features)
    for i, feature in enumerate(prop.features):
        scenes.append(Scene(kind="feature", caption=feature, label=f"FEATURE {i + 1} OF {total}"))

    middle = len(scenes) - 1
    target_middle = max(MIN_FEATURE_SCENES if image_count > 1 else middle, image_count - 2)
    while middle < target_middle and len(scenes) + 1 < MAX_SCENES:
        scenes.append(Scene(kind="gallery", caption=prop.location or prop.name, label="TAKE A CLOSER LOOK"))
        middle += 1

    scenes.append(Scene(kind="cta", caption=prop.cta or GENERIC_CTA, label=prop.name.upper()))
    _assign_images(scenes, image_count)
    return scenes


# --------------------------------------------------------------------------- template writer

def template_script(prop: PropertyInput, image_count: int) -> Script:
    scenes = scene_plan(prop, image_count)
    feature_i = 0
    for scene in scenes:
        if scene.kind == "title":
            line = f"Presenting {prop.name}"
            if prop.property_type:
                line += f", {_article(prop.property_type)} {prop.property_type}"
            if prop.location:
                line += f" in {prop.location}"
            narration = _sentence(line)
            if prop.price:
                narration += f" Priced at {prop.price}."
            scene.narration = narration
        elif scene.kind == "feature":
            is_last = feature_i == len(prop.features) - 1 and feature_i > 1
            lead = _FEATURE_LEADS[-1] if is_last else _FEATURE_LEADS[min(feature_i, len(_FEATURE_LEADS) - 2)]
            text = scene.caption.rstrip(".")
            scene.narration = lead.format(F=text, f=_lower_first(text))
            feature_i += 1
        elif scene.kind == "cta":
            parts = [_sentence(prop.cta or GENERIC_CTA)]
            if prop.contact:
                starts_with_verb = re.match(_CONTACT_VERBS, prop.contact, flags=re.I)
                parts.append(_sentence(prop.contact) if starts_with_verb else f"Contact {prop.contact}.")
            scene.narration = " ".join(parts)
        # gallery scenes stay music-only
    return Script(scenes=scenes, source="template")


def _article(word: str) -> str:
    first = word.strip()[:1].lower()
    # "an apartment", but "a 2 BHK flat" and "a villa"
    return "an" if first in "aeio" else "a"


# --------------------------------------------------------------------------- fact checker

# Words that make a factual claim about a property. If the AI uses one, the input must contain it too.
CLAIM_TERMS = [
    "pool", "swimming", "gym", "fitness", "clubhouse", "club", "garden", "park", "lawn", "terrace",
    "balcony", "rooftop", "view", "sea", "beach", "lake", "river", "hill", "mountain", "metro",
    "station", "airport", "highway", "school", "hospital", "mall", "market", "office", "it park",
    "parking", "garage", "lift", "elevator", "security", "cctv", "gated", "power backup", "backup",
    "furnished", "semi-furnished", "modular", "vastu", "east-facing", "west-facing", "north-facing",
    "south-facing", "corner", "duplex", "penthouse", "villa", "studio", "loan", "rera", "approved",
    "possession", "ready to move", "ready-to-move", "new launch", "resale", "freehold", "leasehold",
    "discount", "offer", "free", "investment", "returns", "appreciation", "rental", "pet",
    "spa", "jacuzzi", "sauna", "tennis", "playground", "jogging", "temple", "minutes", "mins", "km",
]
SUPERLATIVES = [
    "best", "cheapest", "lowest", "largest", "biggest", "guaranteed", "guarantee", "number one",
    "#1", "unbeatable", "finest", "most affordable", "only", "first-ever", "world-class", "award",
]
NUMBER_WORDS = {
    "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7",
    "eight": "8", "nine": "9", "ten": "10", "eleven": "11", "twelve": "12", "twenty": "20",
    "fifty": "50", "hundred": "100", "thousand": "1000", "dozen": "12", "double": "2",
}
_STOPWORDS = {"the", "a", "an", "and", "with", "of", "in", "for", "to", "your", "on", "at", "by", "is", "all"}


def _norm(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9#.]+", " ", text.lower().replace(",", "")) + " "


def _numbers(text: str) -> set[str]:
    return {n.rstrip(".") for n in re.findall(r"\d+(?:\.\d+)?", text.replace(",", ""))}


def _contains_term(norm_text: str, term: str) -> bool:
    # whole-word match, with an optional plural "s"
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}s?(?![a-z0-9])", norm_text) is not None


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS and len(w) > 1}


def fact_check(script: Script, prop: PropertyInput) -> list[str]:
    """Return a list of problems. An empty list means every claim is backed by the input."""
    issues: list[str] = []
    facts = prop.facts_text()
    facts_norm = _norm(facts)
    fact_numbers = _numbers(facts)
    allowed_words = set(facts_norm.split())

    for i, scene in enumerate(script.scenes):
        for field_name, text in (("caption", scene.caption), ("narration", scene.narration)):
            where = f"scene {i + 1} {field_name}"
            if field_name == "caption" and len(text) > MAX_CAPTION_CHARS:
                issues.append(f"{where} is too long for the screen ({len(text)} chars)")
            if field_name == "narration" and len(text) > MAX_NARRATION_CHARS:
                issues.append(f"{where} is too long ({len(text)} chars)")

            for number in _numbers(text) - fact_numbers:
                issues.append(f"{where} mentions the number {number}, which is not in the input")
            text_norm = _norm(text)
            for word, digit in NUMBER_WORDS.items():
                if _contains_term(text_norm, word) and digit not in fact_numbers and word not in allowed_words:
                    issues.append(f"{where} says \"{word}\", which is not backed by the input")
            for term in CLAIM_TERMS:
                if _contains_term(text_norm, term) and not _contains_term(facts_norm, term):
                    issues.append(f"{where} claims \"{term}\", which is not in the input")
            for term in SUPERLATIVES:
                if _contains_term(text_norm, term) and not _contains_term(facts_norm, term):
                    issues.append(f"{where} uses the unsupported claim \"{term}\"")

    # each feature scene must still be about its own feature
    features = [s for s in script.scenes if s.kind == "feature"]
    for scene, feature in zip(features, prop.features):
        if not (_words(scene.caption) & _words(feature)):
            issues.append(f"caption \"{scene.caption}\" does not match the feature \"{feature}\"")
    return issues


# --------------------------------------------------------------------------- AI writer

_SYSTEM_PROMPT = """You write voice-over and on-screen captions for short real-estate promo videos.
Strict rules:
- Use ONLY facts present in the listing JSON. Do not add amenities, distances, views, nearby places,
  numbers, offers, ratings or superlatives (best, cheapest, guaranteed...) that the listing does not state.
- You may rephrase for warmth and flow, but keep every number exactly as written in the listing.
- Captions: max 45 characters, punchy, no trailing period. Narration: one or two short sentences, max 30 words.
- features[i] must describe listing feature i, in the same order, one entry per listing feature.
- Plain English, no emojis, no hashtags."""

_SCHEMA = {
    "type": "object",
    "properties": {
        "title_narration": {"type": "string"},
        "features": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"caption": {"type": "string"}, "narration": {"type": "string"}},
                "required": ["caption", "narration"],
                "additionalProperties": False,
            },
        },
        "cta_caption": {"type": "string"},
        "cta_narration": {"type": "string"},
    },
    "required": ["title_narration", "features", "cta_caption", "cta_narration"],
    "additionalProperties": False,
}


def _listing_json(prop: PropertyInput) -> str:
    return json.dumps(
        {
            "name": prop.name,
            "location": prop.location,
            "price": prop.price,
            "property_type": prop.property_type,
            "features": prop.features,
            "call_to_action": prop.cta,
            "contact": prop.contact,
        },
        ensure_ascii=False,
        indent=2,
    )


def request_ai_copy(prop: PropertyInput) -> dict:
    """Call Claude once and return the parsed JSON. Raises RuntimeError on any failure."""
    import anthropic  # imported lazily so the template mode works without the SDK configured

    client = anthropic.Anthropic(timeout=60.0, max_retries=2)
    try:
        response = client.beta.messages.create(
            model=config.claude_model(),
            max_tokens=4000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": _SCHEMA}},
            system=_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": "Write the video copy for this listing:\n" + _listing_json(prop),
            }],
        )
    except anthropic.AuthenticationError as exc:
        raise RuntimeError("the API key was rejected") from exc
    except anthropic.RateLimitError as exc:
        raise RuntimeError("rate limited by the API, try again later") from exc
    except anthropic.APIStatusError as exc:
        raise RuntimeError(f"API error {exc.status_code}") from exc
    except anthropic.APIConnectionError as exc:
        raise RuntimeError("could not reach the API (check your internet connection)") from exc

    if response.stop_reason == "refusal":
        raise RuntimeError("the model declined the request")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("the response was cut off")
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("the response was not valid JSON") from exc


def ai_script(prop: PropertyInput, image_count: int, copy: dict) -> Script:
    """Fill the fixed scene plan with AI copy. Structure and feature order stay ours."""
    scenes = scene_plan(prop, image_count)
    ai_features = copy.get("features") or []
    if len(ai_features) != len(prop.features):
        raise RuntimeError(f"expected {len(prop.features)} feature entries, got {len(ai_features)}")

    feature_i = 0
    for scene in scenes:
        if scene.kind == "title":
            scene.narration = str(copy["title_narration"]).strip()
        elif scene.kind == "feature":
            item = ai_features[feature_i]
            scene.caption = str(item["caption"]).strip().rstrip(".")
            scene.narration = str(item["narration"]).strip()
            feature_i += 1
        elif scene.kind == "cta":
            scene.caption = str(copy["cta_caption"]).strip().rstrip(".") or scene.caption
            scene.narration = str(copy["cta_narration"]).strip()
    return Script(scenes=scenes, source="ai")


def write_script(prop: PropertyInput, image_count: int, use_ai: bool = False) -> tuple[Script, list[str]]:
    """Return (script, warnings). AI mode always falls back to the template on any problem."""
    warnings: list[str] = []
    if use_ai:
        if not config.has_api_key():
            warnings.append("AI script requested but ANTHROPIC_API_KEY is not set: using the template script.")
        else:
            try:
                script = ai_script(prop, image_count, request_ai_copy(prop))
                issues = fact_check(script, prop)
                if not issues:
                    return script, warnings
                warnings.append(
                    "AI script failed the fact check, so the template script was used: " + "; ".join(issues[:3])
                )
            except (RuntimeError, KeyError, TypeError) as exc:
                warnings.append(f"AI script unavailable ({exc}): using the template script.")
    return template_script(prop, image_count), warnings
