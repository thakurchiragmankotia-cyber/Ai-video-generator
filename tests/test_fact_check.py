from propvid.models import PropertyInput, Scene, Script
from propvid.script_writer import fact_check

PROP = PropertyInput(
    name="Skyline Residency",
    location="Whitefield, Bengaluru",
    price="₹85 Lakh",
    property_type="2 BHK Apartment",
    features=["1,150 sq ft carpet area", "Modular kitchen", "East-facing balcony"],
    contact="Call +91 90000 00000",
)


def _script(narration: str, captions=None) -> Script:
    captions = captions or PROP.features
    scenes = [Scene("title", PROP.name, narration)]
    scenes += [Scene("feature", c, "") for c in captions]
    scenes.append(Scene("cta", "Book a visit", ""))
    return Script(scenes)


def test_supported_copy_passes():
    assert fact_check(_script("Skyline Residency: a 2 BHK in Whitefield for ₹85 Lakh."), PROP) == []


def test_number_words_backed_by_digits_pass():
    assert fact_check(_script("A two-bedroom home in Whitefield."), PROP) == []


def test_invented_number_fails():
    issues = fact_check(_script("Only 10 minutes from everything."), PROP)
    assert any("10" in i for i in issues)


def test_invented_number_word_fails():
    assert fact_check(_script("Three spacious bedrooms."), PROP)


def test_invented_amenity_fails():
    issues = fact_check(_script("Relax by the swimming pool."), PROP)
    assert any("pool" in i for i in issues)


def test_superlative_fails():
    issues = fact_check(_script("The best deal in Bengaluru."), PROP)
    assert any("best" in i for i in issues)


def test_amenity_in_input_passes():
    assert fact_check(_script("Wake up to your east-facing balcony."), PROP) == []


def test_caption_must_match_its_feature():
    issues = fact_check(_script("Welcome.", captions=["Rooftop garden", "Modular kitchen", "East-facing balcony"]), PROP)
    assert any("does not match" in i for i in issues)


def test_too_long_caption_fails():
    long_caption = "1,150 sq ft carpet area " * 4
    issues = fact_check(_script("Welcome.", captions=[long_caption, "Modular kitchen", "East-facing balcony"]), PROP)
    assert any("too long" in i for i in issues)
