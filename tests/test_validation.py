import pytest

from propvid.errors import InputError
from propvid.validation import MAX_FEATURES, MAX_IMAGES, build_property, parse_features


def test_valid_listing(listing, make_images):
    listing["images"] = [str(p) for p in make_images(4)]
    prop, warnings = build_property(listing)
    assert prop.name == "Skyline Residency"
    assert len(prop.features) == 4
    assert len(prop.image_paths) == 4
    assert warnings == []


def test_missing_name_is_blocking(listing):
    listing["name"] = "   "
    with pytest.raises(InputError, match="name is required"):
        build_property(listing)


def test_non_dict_input():
    with pytest.raises(InputError):
        build_property(["not", "a", "dict"])


def test_too_long_field(listing):
    listing["price"] = "x" * 200
    with pytest.raises(InputError, match="too long"):
        build_property(listing)


def test_missing_optional_fields_warn(make_images):
    prop, warnings = build_property({"name": "Plot 7", "images": [str(p) for p in make_images(4)]})
    text = " ".join(warnings)
    assert "price" in text and "location" in text and "features" in text and "contact" in text
    assert prop.features == []


def test_features_from_text_block():
    assert parse_features("- Pool\n• Gym\n\n3) Park\nGym") == ["Pool", "Gym", "Park"]


def test_features_comma_separated_single_line():
    assert parse_features("Fully furnished, Close to IT parks") == ["Fully furnished", "Close to IT parks"]


def test_too_many_features_are_trimmed(listing):
    listing["features"] = [f"Feature {i}" for i in range(9)]
    prop, warnings = build_property(listing)
    assert len(prop.features) == MAX_FEATURES
    assert any("only the first" in w for w in warnings)


def test_missing_and_unsupported_images_are_skipped(listing, make_images, tmp_path):
    good = make_images(2)
    doc = tmp_path / "notes.txt"
    doc.write_text("hello")
    listing["images"] = [str(good[0]), "nope.jpg", str(doc), str(good[1])]
    prop, warnings = build_property(listing)
    assert prop.image_paths == good
    assert any("not found" in w for w in warnings)
    assert any("Unsupported" in w for w in warnings)


def test_too_many_images_trimmed(listing, make_images):
    listing["images"] = [str(p) for p in make_images(10)]
    prop, warnings = build_property(listing)
    assert len(prop.image_paths) == MAX_IMAGES
    assert any("only the first" in w for w in warnings)


def test_relative_paths_resolve_against_base_dir(listing, make_images, tmp_path):
    make_images(1)
    listing["images"] = ["img_0.jpg"]
    prop, _ = build_property(listing, base_dir=tmp_path)
    assert prop.image_paths == [tmp_path / "img_0.jpg"]
