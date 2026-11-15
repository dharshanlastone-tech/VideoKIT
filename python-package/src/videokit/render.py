"""Output-quality choices shared by final video renders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Quality = Literal["draft", "balanced", "high"]

_QUALITY_SETTINGS: dict[Quality, tuple[str, int]] = {
    "draft": ("veryfast", 28),
    "balanced": ("medium", 22),
    "high": ("slow", 18),
}


@dataclass(frozen=True)
class RenderSettings:
    """Simple, reusable quality settings for final video output.

    ``draft`` renders faster with lower image quality; ``balanced`` is the
    everyday default; ``high`` prioritizes image quality at the cost of longer
    render time and larger files.

    Example:
        settings = RenderSettings(quality="high")
        timeline.export("final.mp4", settings=settings)
        timeline.render("quick-check.mp4", quality="draft")
    """

    quality: Quality = "balanced"

    def __post_init__(self) -> None:
        if not isinstance(self.quality, str) or self.quality not in _QUALITY_SETTINGS:
            choices = ", ".join(_QUALITY_SETTINGS)
            raise ValueError(f"quality must be one of: {choices}.")

    @property
    def preset(self) -> str:
        """FFmpeg x264 speed preset selected for this quality level."""
        return _QUALITY_SETTINGS[self.quality][0]

    @property
    def crf(self) -> int:
        """FFmpeg constant-rate-factor value; lower means higher quality."""
        return _QUALITY_SETTINGS[self.quality][1]

    @property
    def audio_bitrate(self) -> str:
        """AAC bitrate used for final renders."""
        return "192k"
