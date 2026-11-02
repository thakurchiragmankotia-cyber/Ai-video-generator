from PIL import Image

from propvid.images import cover_fit, load_images, placeholder


def test_corrupt_image_becomes_warning(make_images, tmp_path):
    good = make_images(4)
    bad = tmp_path / "broken.jpg"
    bad.write_bytes(b"definitely not a jpeg")
    images, warnings = load_images(good + [bad])
    assert len(images) == 4
    assert any("broken.jpg" in w for w in warnings)


def test_no_images_warns_placeholder(tmp_path):
    images, warnings = load_images([])
    assert images == []
    assert any("placeholder" in w for w in warnings)


def test_few_images_warns_reuse(make_images):
    images, warnings = load_images(make_images(2))
    assert len(images) == 2
    assert any("reused" in w for w in warnings)


def test_exif_rotation_is_applied(tmp_path):
    img = Image.new("RGB", (800, 400), "red")
    exif = Image.Exif()
    exif[0x0112] = 6  # orientation: rotate 90 degrees clockwise
    path = tmp_path / "rotated.jpg"
    img.save(path, exif=exif)
    images, _ = load_images([path])
    assert images[0].size == (400, 800)


def test_cover_fit_has_exact_size():
    out = cover_fit(Image.new("RGB", (1000, 300)), (720, 1280))
    assert out.size == (720, 1280)


def test_placeholder_size():
    assert placeholder((320, 180)).size == (320, 180)
