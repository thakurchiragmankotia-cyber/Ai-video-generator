"""Render options and environment settings. Environment variables are read here only."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

FRAME_SIZES = {
    "vertical": (720, 1280),
    "horizontal": (1280, 720),
}
DEFAULT_CLAUDE_MODEL = "claude-opus-5-5"


def _env_fps() -> int:
    try:
        return max(12, min(60, int(os.getenv("PROPVID_FPS", "24"))))
    except ValueError:
        return 24


@dataclass
class RenderOptions:
    orientation: str = "vertical"
    narration: bool = True
    music: bool = True
    use_ai: bool = False
    fps: int = field(default_factory=_env_fps)

    def __post_init__(self) -> None:
        if self.orientation not in FRAME_SIZES:
            raise ValueError(f"orientation must be one of {sorted(FRAME_SIZES)}")

    @property
    def size(self) -> tuple[int, int]:
        return FRAME_SIZES[self.orientation]


def claude_model() -> str:
    return os.getenv("PROPVID_CLAUDE_MODEL") or DEFAULT_CLAUDE_MODEL


def has_api_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
