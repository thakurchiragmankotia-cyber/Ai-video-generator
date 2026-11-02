import pytest

from propvid import script_writer
from propvid.models import PropertyInput
from propvid.script_writer import fact_check, scene_plan, speakable, template_script, write_script
from propvid.validation import build_property


@pytest.fixture
def prop(listing):
    return build_property(listing)[0]


def test_template_structure(prop):
    script = template_script(prop, image_count=6)
    kinds = [s.kind for s in script.scenes]
    assert kinds[0] == "title" and kinds[-1] == "cta"
    assert kinds.count("feature") == 4
    assert script.source == "template"
    assert all(s.image_index is not None for s in script.scenes)


def test_template_uses_only_input_facts(prop):
    assert fact_check(template_script(prop, 6), prop) == []


def test_template_mentions_price_and_contact(prop):
    script = template_script(prop, 6)
    assert "₹85 Lakh" in script.scenes[0].narration
    assert "Call +91 90000 00000" in script.scenes[-1].narration
    assert "Contact Call" not in script.scenes[-1].narration


def test_gallery_scenes_pad_short_feature_lists():
    prop = PropertyInput(name="Plot 7", location="Baner, Pune", features=["Corner plot"])
    kinds = [s.kind for s in scene_plan(prop, image_count=5)]
    assert kinds == ["title", "feature", "gallery", "gallery", "cta"]


def test_scene_count_is_capped():
    prop = PropertyInput(name="X", features=[f"F{i}" for i in range(5)])
    assert len(scene_plan(prop, image_count=8)) <= script_writer.MAX_SCENES


def test_no_images_means_placeholders():
    prop = PropertyInput(name="X", features=["A", "B", "C"])
    assert all(s.image_index is None for s in scene_plan(prop, image_count=0))


def test_generic_cta_when_missing():
    script = template_script(PropertyInput(name="X"), 0)
    assert script.scenes[-1].caption == script_writer.GENERIC_CTA


def test_speakable_rewrites_symbols():
    text = speakable("₹85 Lakh, 1,150 sq ft, 2 BHK. Call +91 90000 12345")
    assert "85 Lakh rupees" in text
    assert "square feet" in text
    assert "B H K" in text
    assert "9 1 9 0 0 0 0 1 2 3 4 5" in text


def test_ai_requested_without_key_falls_back(prop, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    script, warnings = write_script(prop, 6, use_ai=True)
    assert script.source == "template"
    assert any("ANTHROPIC_API_KEY" in w for w in warnings)


def _ai_copy(prop, **overrides):
    copy = {
        "title_narration": f"Welcome to {prop.name} in {prop.location}, at {prop.price}.",
        "features": [{"caption": f, "narration": f"Enjoy {f.lower()}."} for f in prop.features],
        "cta_caption": "Book your site visit today",
        "cta_narration": "Book your site visit today. Call +91 90000 00000.",
    }
    copy.update(overrides)
    return copy


def test_ai_copy_that_passes_fact_check_is_used(prop, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(script_writer, "request_ai_copy", lambda p: _ai_copy(p))
    script, warnings = write_script(prop, 6, use_ai=True)
    assert script.source == "ai"
    assert warnings == []


def test_ai_copy_with_invented_facts_falls_back(prop, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    bad = _ai_copy(prop, title_narration="The best sea-view home, just 5 minutes from the metro!")
    monkeypatch.setattr(script_writer, "request_ai_copy", lambda p: bad)
    script, warnings = write_script(prop, 6, use_ai=True)
    assert script.source == "template"
    assert any("fact check" in w for w in warnings)


def test_ai_failure_falls_back(prop, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def boom(p):
        raise RuntimeError("could not reach the API")

    monkeypatch.setattr(script_writer, "request_ai_copy", boom)
    script, warnings = write_script(prop, 6, use_ai=True)
    assert script.source == "template"
    assert any("could not reach" in w for w in warnings)


def test_ai_wrong_feature_count_falls_back(prop, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(script_writer, "request_ai_copy", lambda p: _ai_copy(p, features=[]))
    script, warnings = write_script(prop, 6, use_ai=True)
    assert script.source == "template"
