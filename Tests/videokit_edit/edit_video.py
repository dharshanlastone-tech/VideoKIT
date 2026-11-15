"""Create polished VideoKit edits from Tests/Untitled Project.mp4.

Run from the repository root:

    python Tests/videokit_edit/edit_video.py

The source file is never modified. Outputs are written to
Tests/videokit_edit/output.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from videokit import RenderSettings, Timeline, Video

from edit_plan import (
    DIRECTORS_CROSSFADE,
    DIRECTORS_CUT,
    DIRECTORS_CUT_SCENES,
    DIRECTORS_QUALITY,
    EDIT_PLAN_JSON,
    FPS,
    GRADE,
    HEIGHT,
    OUTPUT_DIR,
    POSTER,
    REPO_ROOT,
    SOURCE,
    SOURCE_DURATION,
    STORY_TRAILER,
    STORY_TRAILER_SCENES,
    THUMBNAIL,
    TRAILER_CROSSFADE,
    TRAILER_QUALITY,
    WIDTH,
    Scene,
    timeline_duration,
    validate_scenes,
)


def apply_grade(clip):
    """Apply a restrained, warm picture grade to one clip."""
    return (
        clip.brightness(GRADE["brightness"])
        .contrast(GRADE["contrast"])
        .saturation(GRADE["saturation"])
    )


def build_timeline(
    video: Video,
    scenes: tuple[Scene, ...],
    crossfade: float,
    *,
    fade_in: float = 0.0,
    fade_out: float = 0.0,
) -> Timeline:
    """Build a graded timeline with optional opening and closing fades."""
    timeline = Timeline()
    last_index = len(scenes) - 1
    for index, scene in enumerate(scenes):
        clip = apply_grade(video.cut(scene.start, scene.end))
        if index == 0 and fade_in:
            clip = clip.fade_in(fade_in)
        if index == last_index and fade_out:
            clip = clip.fade_out(fade_out)
        timeline.add(clip, crossfade=0.0 if index == 0 else crossfade)
    return timeline


def render_directors_cut(video: Video) -> Path:
    """Render the complete story with soft scene transitions and high quality."""
    timeline = build_timeline(
        video,
        DIRECTORS_CUT_SCENES,
        DIRECTORS_CROSSFADE,
        fade_in=1.0,
        fade_out=2.0,
    )
    settings = RenderSettings(quality=DIRECTORS_QUALITY)
    timeline.export(
        DIRECTORS_CUT,
        overwrite=True,
        width=WIDTH,
        height=HEIGHT,
        fps=FPS,
        settings=settings,
    )
    return DIRECTORS_CUT


def render_story_trailer(video: Video) -> Path:
    """Render a fast, sentence-complete 47-second retelling of the story."""
    timeline = build_timeline(
        video,
        STORY_TRAILER_SCENES,
        TRAILER_CROSSFADE,
        fade_in=0.6,
        fade_out=0.8,
    )
    timeline.render(
        STORY_TRAILER,
        quality=TRAILER_QUALITY,
        overwrite=True,
        width=WIDTH,
        height=HEIGHT,
        fps=FPS,
    )
    return STORY_TRAILER


def render_stills(video: Video) -> tuple[Path, Path]:
    """Extract a poster and a small thumbnail from the finished story."""
    video.extract_frame(60.0, POSTER, overwrite=True)
    video.thumbnail(
        THUMBNAIL,
        timestamp=227.0,
        max_width=540,
        max_height=675,
        overwrite=True,
    )
    return POSTER, THUMBNAIL


def _display(path: Path) -> str:
    """Use repository-relative paths in the saved plan when possible."""
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def write_plan() -> Path:
    """Write a machine-readable record of every edit decision."""
    plan = {
        "source": _display(SOURCE),
        "source_duration": SOURCE_DURATION,
        "output_size": [WIDTH, HEIGHT],
        "output_fps": FPS,
        "grade": GRADE,
        "directors_cut": {
            "path": _display(DIRECTORS_CUT),
            "crossfade": DIRECTORS_CROSSFADE,
            "expected_duration": round(
                timeline_duration(DIRECTORS_CUT_SCENES, DIRECTORS_CROSSFADE), 3
            ),
            "scenes": [
                {"start": scene.start, "end": scene.end, "title": scene.title}
                for scene in DIRECTORS_CUT_SCENES
            ],
        },
        "story_trailer": {
            "path": _display(STORY_TRAILER),
            "crossfade": TRAILER_CROSSFADE,
            "expected_duration": round(
                timeline_duration(STORY_TRAILER_SCENES, TRAILER_CROSSFADE), 3
            ),
            "scenes": [
                {"start": scene.start, "end": scene.end, "title": scene.title}
                for scene in STORY_TRAILER_SCENES
            ],
        },
        "stills": {"poster": _display(POSTER), "thumbnail": _display(THUMBNAIL)},
    }
    EDIT_PLAN_JSON.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return EDIT_PLAN_JSON


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stills",
        action="store_true",
        help="Render only the poster and thumbnail.",
    )
    parser.add_argument(
        "--trailer",
        action="store_true",
        help="Render only the 47-second story trailer.",
    )
    parser.add_argument(
        "--cut",
        action="store_true",
        help="Render only the full director's cut.",
    )
    args = parser.parse_args()
    selected = args.stills or args.trailer or args.cut
    do_all = not selected

    if not SOURCE.is_file():
        raise SystemExit(f"Source video not found: {SOURCE}")
    validate_scenes(DIRECTORS_CUT_SCENES, crossfade=DIRECTORS_CROSSFADE)
    validate_scenes(
        STORY_TRAILER_SCENES,
        duration=SOURCE_DURATION,
        crossfade=TRAILER_CROSSFADE,
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    video = Video(SOURCE)
    print(f"Source: {SOURCE}")
    print(f"Source metadata: {video.width}x{video.height}, {video.fps} fps, {video.duration:.2f}s")
    print(f"Plan: {write_plan()}")

    if do_all or args.stills:
        print("Rendering poster and thumbnail...", flush=True)
        for path in render_stills(video):
            print(f"  {path.name}: {path.stat().st_size / 1024:.1f} KB")

    if do_all or args.trailer:
        print("Rendering the 47-second story trailer...", flush=True)
        trailer = render_story_trailer(video)
        print(f"  {trailer.name}: {trailer.stat().st_size / (1024 * 1024):.1f} MB")

    if do_all or args.cut:
        print("Rendering the full director's cut...", flush=True)
        cut = render_directors_cut(video)
        print(f"  {cut.name}: {cut.stat().st_size / (1024 * 1024):.1f} MB")

    print("Done. Outputs are in:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
