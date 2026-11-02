"""Plain data objects passed between pipeline stages."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PropertyInput:
    name: str
    location: str = ""
    price: str = ""
    property_type: str = ""
    features: list[str] = field(default_factory=list)
    cta: str = ""
    contact: str = ""
    image_paths: list[Path] = field(default_factory=list)

    def facts_text(self) -> str:
        """Every fact the user supplied, as one string. Used by the fact checker."""
        parts = [self.name, self.location, self.price, self.property_type, self.cta, self.contact]
        return " \n".join(p for p in parts + self.features if p)


@dataclass
class Scene:
    kind: str                      # "title" | "feature" | "gallery" | "cta"
    caption: str                   # main on-screen text
    narration: str = ""            # spoken text ("" = music only)
    image_index: int | None = None # index into the loaded images; None = placeholder
    label: str = ""                # small uppercase label above the caption
    duration: float = 0.0          # filled in by the pipeline


@dataclass
class Script:
    scenes: list[Scene]
    source: str = "template"       # "template" | "ai"

    @property
    def narration_text(self) -> str:
        return " ".join(s.narration for s in self.scenes if s.narration)
