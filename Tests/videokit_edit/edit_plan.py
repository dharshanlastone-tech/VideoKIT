"""Edit decisions and shared settings for the VideoKit Tests project.

The source video is the local file ``Tests/Untitled Project.mp4``. The edit is
non-destructive: VideoKit reads the source and writes new files under
``Tests/videokit_edit/output``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_DIR.parents[1]
SOURCE = REPO_ROOT / "Tests" / "Untitled Project.mp4"
OUTPUT_DIR = PROJECT_DIR / "output"

DIRECTORS_CUT = OUTPUT_DIR / "videokit_directors_cut.mp4"
STORY_TRAILER = OUTPUT_DIR / "videokit_story_trailer.mp4"
POSTER = OUTPUT_DIR / "videokit_poster.jpg"
THUMBNAIL = OUTPUT_DIR / "videokit_thumbnail.jpg"
EDIT_PLAN_JSON = OUTPUT_DIR / "edit_plan.json"

SOURCE_DURATION = 255.25
WIDTH = 1080
HEIGHT = 1350
FPS = 30

DIRECTORS_CROSSFADE = 0.45
TRAILER_CROSSFADE = 0.5
DIRECTORS_QUALITY = "high"
TRAILER_QUALITY = "high"

GRADE = {
    "brightness": 0.015,
    "contrast": 1.08,
    "saturation": 1.12,
}


@dataclass(frozen=True)
class Scene:
    """One source-video interval in an edit."""

    start: float
    end: float
    title: str

    @property
    def duration(self) -> float:
        return self.end - self.start


# The hard scene changes detected in the source are approximately 27.6, 75.2,
# 203.9, and 241.0 seconds. The director's cut keeps the complete story and
# softens those cuts with short crossfades.
DIRECTORS_CUT_SCENES = (
    Scene(0.0, 27.6, "The village and the question"),
    Scene(27.6, 75.2, "Twinkle falls into the garden"),
    Scene(75.2, 203.9, "Gravity, energy, and the long night"),
    Scene(203.9, 240.966667, "Twinkle returns to the sky"),
    Scene(240.966667, 255.25, "A final message"),
)

# A sentence-complete, 47-second retelling of the story. These ranges come from
# the narration timestamps, so the trailer does not cut off a spoken sentence.
STORY_TRAILER_SCENES = (
    Scene(0.0, 5.6, "Once upon a time"),
    Scene(35.6, 41.88, "A tiny star falls"),
    Scene(57.16, 61.88, "Glowing faintly"),
    Scene(95.28, 99.58, "It is physics"),
    Scene(123.36, 128.7, "Gravity gives energy"),
    Scene(169.16, 177.16, "Listening to the night"),
    Scene(196.96, 201.6, "Twinkle shines"),
    Scene(212.32, 216.88, "Back to the sky"),
    Scene(231.48, 239.48, "Keep exploring"),
)


def validate_scenes(
    scenes: tuple[Scene, ...],
    *,
    duration: float = SOURCE_DURATION,
    crossfade: float = 0.0,
) -> None:
    """Raise ValueError if an edit cannot be built from the scenes."""
    if not scenes:
        raise ValueError("At least one scene is required.")
    if crossfade < 0:
        raise ValueError("crossfade cannot be negative.")
    previous_end = 0.0
    for scene in scenes:
        if scene.start < 0 or scene.end <= scene.start:
            raise ValueError(f"Invalid scene range: {scene.title}.")
        if scene.end > duration + 1e-6:
            raise ValueError(f"Scene exceeds the source duration: {scene.title}.")
        if scene.start < previous_end - 1e-6:
            raise ValueError("Scenes must be in source order and must not overlap.")
        if crossfade >= scene.duration:
            raise ValueError(f"Crossfade is too long for scene: {scene.title}.")
        previous_end = scene.end


def timeline_duration(scenes: tuple[Scene, ...], crossfade: float) -> float:
    """Return the expected duration after crossfades are applied."""
    return sum(scene.duration for scene in scenes) - crossfade * max(
        0, len(scenes) - 1
    )
