"""Edit decisions and shared settings for the VideoKit Tests project.

The source video is the local file ``Tests/Untitled Project.mp4``. The edit is
non-destructive: VideoKit reads the source and writes new files under
``Tests/videokit_edit/output``.

The source is a 4:5 canvas with a 9:16 illustration pillarboxed inside it. The
masterpiece and its trailer crop that baked-in pillarbox away and deliver a
true 1080x1920 vertical film.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_DIR.parents[1]
SOURCE = REPO_ROOT / "Tests" / "Untitled Project.mp4"
OUTPUT_DIR = PROJECT_DIR / "output"

# Clean 4:5 alternates kept for comparison.
DIRECTORS_CUT = OUTPUT_DIR / "videokit_directors_cut.mp4"
STORY_TRAILER = OUTPUT_DIR / "videokit_story_trailer.mp4"

# The main deliverables: a true 9:16 effects cut and a short vertical trailer.
MASTERPIECE = OUTPUT_DIR / "videokit_masterpiece.mp4"
MASTERPIECE_TRAILER = OUTPUT_DIR / "videokit_masterpiece_trailer.mp4"

POSTER = OUTPUT_DIR / "videokit_poster.jpg"
THUMBNAIL = OUTPUT_DIR / "videokit_thumbnail.jpg"
MASTERPIECE_CONTACT_SHEET = OUTPUT_DIR / "masterpiece_contact_sheet.jpg"
MASTERPIECE_TRAILER_CONTACT_SHEET = OUTPUT_DIR / "masterpiece_trailer_contact_sheet.jpg"
EDIT_PLAN_JSON = OUTPUT_DIR / "edit_plan.json"

SOURCE_DURATION = 255.25

# Primary output: vertical 9:16.
WIDTH = 1080
HEIGHT = 1920

# The clean alternates keep the original 4:5 canvas.
CLEAN_WIDTH = 1080
CLEAN_HEIGHT = 1350

FPS = 30

# The illustration occupies x=164..916 on the 1080-wide 4:5 source canvas.
ARTWORK_X = 164
ARTWORK_WIDTH = 752
ARTWORK_HEIGHT = 1350

# An effect clip is cropped from the already-vertical frame, then scaled up
# before the animated tilt. 1.30 is enough to keep the 1080x1920 crop inside
# the rotated image for every angle used below (the maximum is 7 degrees).
TILT_FRAME_SCALE = 1.30
MAX_TILT_DEGREES = 8.0

DIRECTORS_CROSSFADE = 0.45
TRAILER_CROSSFADE = 0.5
MASTERPIECE_CROSSFADE = 0.35
MASTERPIECE_TRAILER_CROSSFADE = 0.35
DIRECTORS_QUALITY = "high"
TRAILER_QUALITY = "high"
MASTERPIECE_QUALITY = "high"

GRADE = {
    "brightness": 0.015,
    "contrast": 1.08,
    "saturation": 1.12,
}


@dataclass(frozen=True)
class Scene:
    """One source-video interval in an edit.

    The first three fields are enough for a simple cut. The remaining fields
    describe the optional speed ramp, colour grade, and animated punch-in tilt
    used by the effects cuts. ``crossfade=None`` means "use the edit's default
    crossfade"; an explicit ``0.0`` creates a hard cut.
    """

    start: float
    end: float
    title: str
    speed: float = 1.0
    brightness: float = GRADE["brightness"]
    contrast: float = GRADE["contrast"]
    saturation: float = GRADE["saturation"]
    tilt: float = 0.0
    tilt_from: float = 0.0
    zoom: float = 1.25
    crossfade: float | None = None
    fade_in: float = 0.0
    fade_out: float = 0.0

    @property
    def duration(self) -> float:
        """Source duration in seconds."""
        return self.end - self.start

    @property
    def playback_duration(self) -> float:
        """Duration after the speed ramp is applied."""
        return self.duration / self.speed

    @property
    def has_tilt(self) -> bool:
        return self.tilt != 0 or self.tilt_from != 0


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

# The full effects-driven cut. The scene order is contiguous in the source, so
# the narration never jumps. The tilt scenes use a hard cut at the point where
# the effect starts; a 0.0 crossfade keeps the spoken audio seamless.
MASTERPIECE_SCENES = (
    Scene(
        0.0,
        27.6,
        "The village and the question",
        speed=1.05,
        brightness=0.012,
        contrast=1.10,
        saturation=1.16,
        crossfade=0.0,
        fade_in=1.2,
    ),
    Scene(
        27.6,
        35.6,
        "The night sky opens",
        speed=1.10,
        brightness=0.014,
        contrast=1.14,
        saturation=1.18,
        crossfade=0.35,
    ),
    Scene(
        35.6,
        41.88,
        "A tiny star falls",
        speed=1.15,
        brightness=0.016,
        contrast=1.22,
        saturation=1.22,
        tilt=6.0,
        zoom=1.25,
        crossfade=0.0,
    ),
    Scene(
        41.88,
        57.16,
        "Mira finds Twinkle",
        speed=1.12,
        brightness=0.014,
        contrast=1.18,
        saturation=1.20,
        crossfade=0.30,
    ),
    Scene(
        57.16,
        61.88,
        "Glowing faintly",
        speed=0.90,
        brightness=0.018,
        contrast=1.24,
        saturation=1.24,
        tilt=-5.0,
        zoom=1.20,
        crossfade=0.0,
    ),
    Scene(
        61.88,
        75.2,
        "A strange little visitor",
        speed=1.15,
        brightness=0.012,
        contrast=1.20,
        saturation=1.20,
        crossfade=0.25,
    ),
    Scene(
        75.2,
        99.58,
        "Gravity and the birds",
        speed=1.18,
        brightness=0.010,
        contrast=1.16,
        saturation=1.18,
        crossfade=0.35,
    ),
    Scene(
        99.58,
        123.36,
        "It is physics",
        speed=1.22,
        brightness=0.012,
        contrast=1.20,
        saturation=1.20,
        crossfade=0.30,
    ),
    Scene(
        123.36,
        128.7,
        "Gravity gives energy",
        speed=1.20,
        brightness=0.016,
        contrast=1.24,
        saturation=1.24,
        tilt=7.0,
        zoom=1.30,
        crossfade=0.0,
    ),
    Scene(
        128.7,
        147.4,
        "The long night",
        speed=1.18,
        brightness=0.010,
        contrast=1.20,
        saturation=1.20,
        crossfade=0.25,
    ),
    Scene(
        147.4,
        169.16,
        "Listening to the forest",
        speed=0.92,
        brightness=0.004,
        contrast=1.10,
        saturation=1.14,
        crossfade=0.35,
    ),
    Scene(
        169.16,
        172.0,
        "The whisper of the night",
        speed=0.90,
        brightness=0.008,
        contrast=1.16,
        saturation=1.18,
        tilt=3.0,
        zoom=1.15,
        crossfade=0.0,
    ),
    Scene(
        172.0,
        196.96,
        "Keep listening",
        speed=0.90,
        brightness=0.006,
        contrast=1.12,
        saturation=1.16,
        crossfade=0.0,
    ),
    Scene(
        196.96,
        200.0,
        "Twinkle shines",
        speed=0.85,
        brightness=0.020,
        contrast=1.30,
        saturation=1.32,
        tilt=4.0,
        zoom=1.25,
        crossfade=0.0,
    ),
    Scene(
        200.0,
        203.9,
        "The light returns",
        speed=0.95,
        brightness=0.018,
        contrast=1.22,
        saturation=1.24,
        crossfade=0.0,
    ),
    Scene(
        203.9,
        212.32,
        "Twinkle returns to the sky",
        speed=1.02,
        brightness=0.012,
        contrast=1.16,
        saturation=1.18,
        crossfade=0.20,
    ),
    Scene(
        212.32,
        214.8,
        "Higher and higher",
        speed=1.05,
        brightness=0.016,
        contrast=1.22,
        saturation=1.22,
        tilt=-4.0,
        zoom=1.25,
        crossfade=0.0,
    ),
    Scene(
        214.8,
        216.88,
        "Back in place",
        speed=1.0,
        brightness=0.012,
        contrast=1.16,
        saturation=1.18,
        crossfade=0.0,
    ),
    Scene(
        216.88,
        240.966667,
        "A final message",
        speed=0.98,
        brightness=0.008,
        contrast=1.08,
        saturation=1.12,
        crossfade=0.30,
    ),
    Scene(
        240.966667,
        255.25,
        "Keep exploring",
        speed=0.95,
        brightness=0.004,
        contrast=1.06,
        saturation=1.10,
        crossfade=0.0,
        fade_out=2.2,
    ),
)

# A short vertical trailer built from sentence-complete moments and the most
# dramatic tilt beats. It ends before the final subscribe card.
MASTERPIECE_TRAILER_SCENES = (
    Scene(
        0.0,
        5.6,
        "Once upon a time",
        speed=1.05,
        brightness=0.012,
        contrast=1.10,
        saturation=1.16,
        crossfade=0.0,
        fade_in=0.7,
    ),
    Scene(
        35.6,
        41.88,
        "A tiny star falls",
        speed=1.15,
        brightness=0.016,
        contrast=1.22,
        saturation=1.22,
        tilt=6.0,
        zoom=1.25,
        crossfade=0.35,
    ),
    Scene(
        57.16,
        61.88,
        "Glowing faintly",
        speed=0.90,
        brightness=0.018,
        contrast=1.24,
        saturation=1.24,
        tilt=-5.0,
        zoom=1.20,
        crossfade=0.35,
    ),
    Scene(
        95.28,
        99.58,
        "It is physics",
        speed=1.22,
        brightness=0.012,
        contrast=1.22,
        saturation=1.22,
        crossfade=0.35,
    ),
    Scene(
        123.36,
        128.7,
        "Gravity gives energy",
        speed=1.20,
        brightness=0.016,
        contrast=1.24,
        saturation=1.24,
        tilt=7.0,
        zoom=1.30,
        crossfade=0.35,
    ),
    Scene(
        169.16,
        177.16,
        "Listening to the night",
        speed=0.92,
        brightness=0.006,
        contrast=1.12,
        saturation=1.14,
        crossfade=0.35,
    ),
    Scene(
        196.96,
        201.6,
        "Twinkle shines",
        speed=0.85,
        brightness=0.020,
        contrast=1.30,
        saturation=1.32,
        tilt=4.0,
        zoom=1.25,
        crossfade=0.35,
    ),
    Scene(
        212.32,
        216.88,
        "Back to the sky",
        speed=1.05,
        brightness=0.016,
        contrast=1.22,
        saturation=1.22,
        tilt=-4.0,
        zoom=1.25,
        crossfade=0.35,
    ),
    Scene(
        231.48,
        239.48,
        "Keep exploring",
        speed=1.0,
        brightness=0.008,
        contrast=1.10,
        saturation=1.14,
        crossfade=0.35,
        fade_out=0.9,
    ),
)


def required_tilt_scale(degrees: float, *, width: int = WIDTH, height: int = HEIGHT) -> float:
    """Return the smallest safe frame scale for a rotated 9:16 crop."""
    radians = math.radians(abs(degrees))
    return math.cos(radians) + (height / width) * math.sin(radians)


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
        if scene.speed <= 0:
            raise ValueError(f"Speed must be positive: {scene.title}.")
        if not -1 <= scene.brightness <= 1:
            raise ValueError(f"Brightness must be between -1 and 1: {scene.title}.")
        if not 0 <= scene.contrast <= 4:
            raise ValueError(f"Contrast must be between 0 and 4: {scene.title}.")
        if not 0 <= scene.saturation <= 3:
            raise ValueError(f"Saturation must be between 0 and 3: {scene.title}.")
        if scene.has_tilt:
            if abs(scene.tilt) > MAX_TILT_DEGREES:
                raise ValueError(f"Tilt is too large: {scene.title}.")
            if abs(scene.tilt_from) > MAX_TILT_DEGREES:
                raise ValueError(f"Starting tilt is too large: {scene.title}.")
            if not 1 < scene.zoom <= 2:
                raise ValueError(f"Tilt zoom must be between 1 and 2: {scene.title}.")
            if TILT_FRAME_SCALE < required_tilt_scale(
                max(abs(scene.tilt), abs(scene.tilt_from))
            ):
                raise ValueError(f"Tilt frame scale is too small: {scene.title}.")
        chosen_crossfade = crossfade if scene.crossfade is None else scene.crossfade
        if chosen_crossfade < 0:
            raise ValueError(f"Crossfade cannot be negative: {scene.title}.")
        if chosen_crossfade >= scene.playback_duration:
            raise ValueError(f"Crossfade is too long for scene: {scene.title}.")
        if scene.fade_in < 0 or scene.fade_in > scene.playback_duration:
            raise ValueError(f"Fade-in is invalid for scene: {scene.title}.")
        if scene.fade_out < 0 or scene.fade_out > scene.playback_duration:
            raise ValueError(f"Fade-out is invalid for scene: {scene.title}.")
        previous_end = scene.end


def timeline_duration(scenes: tuple[Scene, ...], crossfade: float) -> float:
    """Return the expected duration after speed ramps and crossfades."""
    total = sum(scene.playback_duration for scene in scenes)
    for scene in scenes[1:]:
        chosen_crossfade = crossfade if scene.crossfade is None else scene.crossfade
        total -= chosen_crossfade
    return total


def scene_start(
    scenes: tuple[Scene, ...], index: int, crossfade: float
) -> float:
    """Return the output-timeline start time of one scene."""
    if index < 0 or index >= len(scenes):
        raise IndexError("Scene index is out of range.")
    start = 0.0
    for position in range(index):
        next_scene = scenes[position + 1]
        chosen_crossfade = (
            crossfade if next_scene.crossfade is None else next_scene.crossfade
        )
        start += scenes[position].playback_duration - chosen_crossfade
    return start
