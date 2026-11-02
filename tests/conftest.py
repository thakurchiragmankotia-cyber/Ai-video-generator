import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture
def make_images(tmp_path):
    """Create n small synthetic JPGs and return their paths."""

    def _make(n: int, size=(640, 480)):
        paths = []
        rng = np.random.default_rng(0)
        for i in range(n):
            arr = np.full((size[1], size[0], 3), rng.integers(30, 220, 3), np.uint8)
            path = tmp_path / f"img_{i}.jpg"
            Image.fromarray(arr).save(path)
            paths.append(path)
        return paths

    return _make


@pytest.fixture
def listing():
    return {
        "name": "Skyline Residency",
        "location": "Whitefield, Bengaluru",
        "price": "₹85 Lakh",
        "property_type": "2 BHK Apartment",
        "features": [
            "1,150 sq ft carpet area",
            "Modular kitchen with chimney",
            "Covered parking for 1 car",
            "24x7 security",
        ],
        "cta": "Book your site visit today",
        "contact": "Call +91 90000 00000",
    }
