"""Create polished VideoKit edits from Tests/Untitled Project.mp4.

Run from the repository root:

    python Tests/videokit_edit/edit_video.py

The source file is never modified. Outputs are written to
Tests/videokit_edit/output.

The default run renders the vertical 9:16 effects masterpiece, its short
trailer, the poster/thumbnail, and contact sheets. The original clean 4:5
alternates are still available with ``--cut`` and ``--trailer``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from videokit import RenderSettings, Timeline, Video

from edit_plan import (
    ARTWORK_HEIGHT,
    ARTWORK_WIDTH,
    ARTWORK_X,
    CLEAN_HEIGHT,
    CLEAN_WIDTH,
    DIRECTORS_CROSSFADE,
    DIRECTORS_CUT,
    DIRECTORS_CUT_SCENES,
    DIRECTORS_QUALITY,
    EDIT_PLAN_JSON,
    FPS,
    GRADE,
    HEIGHT,
    MASTERPIECE,
    MASTERPIECE_CONTACT_SHEET,
    MASTERPIECE_CROSSFADE,
    MASTERPIECE_QUALITY,
    MASTERPIECE_SCENES,
    MASTERPIECE_TRAILER,
    MASTERPIECE_TRAILER_CONTACT_SHEET,
    MASTERPIECE_TRAILER_CROSSFADE,
    MASTERPIECE_TRAILER_SCENES,
    OUTPUT_DIR,
    POSTER,
    REPO_ROOT,
    SOURCE,
    SOURCE_DURATION,
    STORY_TRAILER,
    STORY_TRAILER_SCENES,
    THUMBNAIL,
    TILT_FRAME_SCALE,
    TRAILER_CROSSFADE,
    TRAILER_QUALITY,
    WIDTH,
    Scene,
    required_tilt_scale,
    scene_start,
    timeline_duration,
    validate_scenes,
)


def _even(value: int) -> int:
    """Round a positive pixel count to an even number."""
    rounded = int(round(value))
    return rounded if rounded % 2 == 0 else rounded + 1


def _tilt_crop_width(zoom: float) -> int:
    """Return an even 9:16 crop width that is a multiple of 18.

    A multiple of 18 keeps ``width * 16 / 9`` an even integer, so the resize
    step fills the frame exactly and never introduces a pad bar.
    """
    target = int(round(WIDTH / zoom))
    multiple = max(18, int(round(target / 18)) * 18)
    while multiple > WIDTH:
        multiple -= 18
    return multiple


def apply_grade(clip, scene: Scene | None = None):
    """Apply one scene's brightness, contrast, and saturation grade."""
    if scene is None:
        return (
            clip.brightness(GRADE["brightness"])
            .contrast(GRADE["contrast"])
            .saturation(GRADE["saturation"])
        )
    return (
        clip.brightness(scene.brightness)
        .contrast(scene.contrast)
        .saturation(scene.saturation)
    )


def build_timeline(
    video: Video,
    scenes: tuple[Scene, ...],
    crossfade: float,
    *,
    fade_in: float = 0.0,
    fade_out: float = 0.0,
) -> Timeline:
    """Build a clean timeline with optional opening and closing fades."""
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


def build_masterpiece_clip(video: Video, scene: Scene):
    """Build one vertical effects clip from a source range.

    The source illustration is pillarboxed inside a 4:5 canvas. We first crop
    away that baked-in black border, then reframe to 9:16. Tilt scenes get a
    punch-in crop, a 1.3x intermediate upscale, a smooth VideoKit ``tilt()``,
    and a final 1080x1920 crop with no exposed corners.
    """
    clip = video.cut(scene.start, scene.end)
    clip = clip.crop(
        ARTWORK_WIDTH,
        ARTWORK_HEIGHT,
        x=ARTWORK_X,
        y=0,
    )
    clip = clip.speed(scene.speed)
    clip = apply_grade(clip, scene)

    if scene.has_tilt:
        clip = clip.to_vertical(width=WIDTH, height=HEIGHT, mode="crop")

        crop_width = _tilt_crop_width(scene.zoom)
        crop_height = crop_width * 16 // 9
        if crop_width > WIDTH or crop_height > HEIGHT:
            raise ValueError(f"Tilt crop is too large for scene: {scene.title}")
        clip = clip.crop(
            crop_width,
            crop_height,
            x=(WIDTH - crop_width) // 2,
            y=(HEIGHT - crop_height) // 2,
        )

        frame_width = _even(WIDTH * TILT_FRAME_SCALE)
        frame_height = frame_width * 16 // 9
        clip = clip.resize(frame_width, frame_height)
        clip = clip.tilt(
            scene.tilt,
            start=0,
            end=clip.duration,
            from_degrees=scene.tilt_from,
        )

        rotated_width, rotated_height = clip._width, clip._height
        if rotated_width is None or rotated_height is None:
            raise ValueError(f"Tilt size is unknown for scene: {scene.title}")
        clip = clip.crop(
            WIDTH,
            HEIGHT,
            x=(rotated_width - WIDTH) // 2,
            y=(rotated_height - HEIGHT) // 2,
        )
    else:
        clip = clip.to_vertical(width=WIDTH, height=HEIGHT, mode="crop")

    if scene.fade_in:
        clip = clip.fade_in(scene.fade_in)
    if scene.fade_out:
        clip = clip.fade_out(scene.fade_out)
    return clip


def build_masterpiece_timeline(
    video: Video,
    scenes: tuple[Scene, ...],
    crossfade: float,
) -> Timeline:
    """Build the vertical effects timeline, honouring per-scene crossfades."""
    timeline = Timeline()
    for index, scene in enumerate(scenes):
        clip = build_masterpiece_clip(video, scene)
        chosen_crossfade = 0.0 if index == 0 else (
            crossfade if scene.crossfade is None else scene.crossfade
        )
        timeline.add(clip, crossfade=chosen_crossfade)
    return timeline


def render_directors_cut(video: Video) -> Path:
    """Render the complete clean 4:5 story with soft transitions."""
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
        width=CLEAN_WIDTH,
        height=CLEAN_HEIGHT,
        fps=FPS,
        settings=settings,
    )
    return DIRECTORS_CUT


def render_story_trailer(video: Video) -> Path:
    """Render the clean, sentence-complete 47-second 4:5 trailer."""
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
        width=CLEAN_WIDTH,
        height=CLEAN_HEIGHT,
        fps=FPS,
    )
    return STORY_TRAILER


def render_masterpiece(video: Video) -> Path:
    """Render the full vertical effects cut."""
    timeline = build_masterpiece_timeline(
        video,
        MASTERPIECE_SCENES,
        MASTERPIECE_CROSSFADE,
    )
    timeline.export(
        MASTERPIECE,
        overwrite=True,
        width=WIDTH,
        height=HEIGHT,
        fps=FPS,
        settings=RenderSettings(quality=MASTERPIECE_QUALITY),
    )
    return MASTERPIECE


def render_masterpiece_trailer(video: Video) -> Path:
    """Render the short vertical effects trailer."""
    timeline = build_masterpiece_timeline(
        video,
        MASTERPIECE_TRAILER_SCENES,
        MASTERPIECE_TRAILER_CROSSFADE,
    )
    timeline.render(
        MASTERPIECE_TRAILER,
        quality=MASTERPIECE_QUALITY,
        overwrite=True,
        width=WIDTH,
        height=HEIGHT,
        fps=FPS,
    )
    return MASTERPIECE_TRAILER


def render_stills(masterpiece: Path) -> tuple[Path, Path]:
    """Extract the poster and thumbnail from the finished vertical cut."""
    finished = Video(masterpiece)

    # The glow scene and the final village scene are the two strongest stills.
    glow_index = next(
        index
        for index, scene in enumerate(MASTERPIECE_SCENES)
        if scene.title == "Twinkle shines"
    )
    village_index = next(
        index
        for index, scene in enumerate(MASTERPIECE_SCENES)
        if scene.title == "A final message"
    )
    poster_time = scene_start(
        MASTERPIECE_SCENES, glow_index, MASTERPIECE_CROSSFADE
    ) + 1.4
    thumbnail_time = scene_start(
        MASTERPIECE_SCENES, village_index, MASTERPIECE_CROSSFADE
    ) + 8.0

    finished.extract_frame(poster_time, POSTER, overwrite=True)
    finished.thumbnail(
        THUMBNAIL,
        timestamp=thumbnail_time,
        max_width=540,
        max_height=960,
        overwrite=True,
    )
    return POSTER, THUMBNAIL


def render_contact_sheet(
    video_path: Path,
    output_path: Path,
    *,
    frames: int = 12,
    columns: int = 4,
    rows: int = 3,
    frame_width: int = 270,
) -> Path:
    """Create a tiled contact sheet from evenly spaced frames."""
    duration = Video(video_path).duration
    fps = frames / duration
    frame_height = _even(frame_width * HEIGHT / WIDTH)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is not available on PATH.")
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"fps={fps:.9g},scale={frame_width}:{frame_height},tile={columns}x{rows}",
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(
            f"Could not create contact sheet '{output_path}': {result.stderr.strip()}"
        )
    return output_path


def _display(path: Path) -> str:
    """Use repository-relative paths in the saved plan when possible."""
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def _scene_dict(scene: Scene) -> dict[str, object]:
    """Serialize one scene, including only the effects that are active."""
    data: dict[str, object] = {
        "start": scene.start,
        "end": scene.end,
        "title": scene.title,
        "speed": scene.speed,
        "brightness": scene.brightness,
        "contrast": scene.contrast,
        "saturation": scene.saturation,
    }
    if scene.crossfade is not None:
        data["crossfade"] = scene.crossfade
    if scene.has_tilt:
        data["tilt"] = scene.tilt
        data["tilt_from"] = scene.tilt_from
        data["zoom"] = scene.zoom
    if scene.fade_in:
        data["fade_in"] = scene.fade_in
    if scene.fade_out:
        data["fade_out"] = scene.fade_out
    return data


def write_plan() -> Path:
    """Write a machine-readable record of every edit decision."""
    largest_tilt = max(
        (
            max(abs(scene.tilt), abs(scene.tilt_from))
            for scene in MASTERPIECE_SCENES
        ),
        default=0.0,
    )
    plan = {
        "source": _display(SOURCE),
        "source_duration": SOURCE_DURATION,
        "source_artwork": {
            "x": ARTWORK_X,
            "width": ARTWORK_WIDTH,
            "height": ARTWORK_HEIGHT,
        },
        "output_size": [WIDTH, HEIGHT],
        "clean_output_size": [CLEAN_WIDTH, CLEAN_HEIGHT],
        "output_fps": FPS,
        "grade": GRADE,
        "tilt_frame_scale": TILT_FRAME_SCALE,
        "maximum_tilt_scale_needed": round(
            required_tilt_scale(largest_tilt), 4
        ),
        "masterpiece": {
            "path": _display(MASTERPIECE),
            "crossfade": MASTERPIECE_CROSSFADE,
            "expected_duration": round(
                timeline_duration(MASTERPIECE_SCENES, MASTERPIECE_CROSSFADE), 3
            ),
            "scenes": [_scene_dict(scene) for scene in MASTERPIECE_SCENES],
        },
        "masterpiece_trailer": {
            "path": _display(MASTERPIECE_TRAILER),
            "crossfade": MASTERPIECE_TRAILER_CROSSFADE,
            "expected_duration": round(
                timeline_duration(
                    MASTERPIECE_TRAILER_SCENES,
                    MASTERPIECE_TRAILER_CROSSFADE,
                ),
                3,
            ),
            "scenes": [
                _scene_dict(scene) for scene in MASTERPIECE_TRAILER_SCENES
            ],
        },
        "directors_cut": {
            "path": _display(DIRECTORS_CUT),
            "crossfade": DIRECTORS_CROSSFADE,
            "expected_duration": round(
                timeline_duration(DIRECTORS_CUT_SCENES, DIRECTORS_CROSSFADE), 3
            ),
            "scenes": [_scene_dict(scene) for scene in DIRECTORS_CUT_SCENES],
        },
        "story_trailer": {
            "path": _display(STORY_TRAILER),
            "crossfade": TRAILER_CROSSFADE,
            "expected_duration": round(
                timeline_duration(STORY_TRAILER_SCENES, TRAILER_CROSSFADE), 3
            ),
            "scenes": [_scene_dict(scene) for scene in STORY_TRAILER_SCENES],
        },
        "stills": {"poster": _display(POSTER), "thumbnail": _display(THUMBNAIL)},
        "contact_sheets": {
            "masterpiece": _display(MASTERPIECE_CONTACT_SHEET),
            "masterpiece_trailer": _display(MASTERPIECE_TRAILER_CONTACT_SHEET),
        },
    }
    EDIT_PLAN_JSON.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return EDIT_PLAN_JSON


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stills",
        action="store_true",
        help="Render only the poster and thumbnail from the existing masterpiece.",
    )
    parser.add_argument(
        "--masterpiece",
        action="store_true",
        help="Render only the full vertical effects cut.",
    )
    parser.add_argument(
        "--masterpiece-trailer",
        action="store_true",
        help="Render only the short vertical effects trailer.",
    )
    parser.add_argument(
        "--trailer",
        action="store_true",
        help="Render only the clean 47-second 4:5 story trailer.",
    )
    parser.add_argument(
        "--cut",
        action="store_true",
        help="Render only the clean 4:5 director's cut.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Render both clean 4:5 alternates.",
    )
    args = parser.parse_args()
    selected = (
        args.stills
        or args.masterpiece
        or args.masterpiece_trailer
        or args.trailer
        or args.cut
        or args.clean
    )
    do_all = not selected

    if not SOURCE.is_file():
        raise SystemExit(f"Source video not found: {SOURCE}")
    validate_scenes(
        MASTERPIECE_SCENES,
        duration=SOURCE_DURATION,
        crossfade=MASTERPIECE_CROSSFADE,
    )
    validate_scenes(
        MASTERPIECE_TRAILER_SCENES,
        duration=SOURCE_DURATION,
        crossfade=MASTERPIECE_TRAILER_CROSSFADE,
    )
    validate_scenes(
        DIRECTORS_CUT_SCENES,
        duration=SOURCE_DURATION,
        crossfade=DIRECTORS_CROSSFADE,
    )
    validate_scenes(
        STORY_TRAILER_SCENES,
        duration=SOURCE_DURATION,
        crossfade=TRAILER_CROSSFADE,
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    video = Video(SOURCE)
    print(f"Source: {SOURCE}")
    print(
        f"Source metadata: {video.width}x{video.height}, "
        f"{video.fps} fps, {video.duration:.2f}s"
    )
    print(f"Plan: {write_plan()}")

    render_full = do_all or args.masterpiece
    render_vertical_trailer = do_all or args.masterpiece_trailer
    render_clean = args.clean or args.cut or args.trailer
    render_still_images = do_all or args.stills
    render_sheets = do_all or args.masterpiece or args.masterpiece_trailer

    if render_full or render_vertical_trailer:
        print("Rendering the vertical effects cut...", flush=True)
        if render_full:
            masterpiece = render_masterpiece(video)
            print(
                f"  {masterpiece.name}: "
                f"{masterpiece.stat().st_size / (1024 * 1024):.1f} MB"
            )
        if render_vertical_trailer:
            vertical_trailer = render_masterpiece_trailer(video)
            print(
                f"  {vertical_trailer.name}: "
                f"{vertical_trailer.stat().st_size / (1024 * 1024):.1f} MB"
            )

    if render_still_images:
        if not MASTERPIECE.is_file():
            raise SystemExit(
                "The vertical masterpiece is missing. Render it first with "
                "--masterpiece."
            )
        print("Rendering poster and thumbnail...", flush=True)
        for path in render_stills(MASTERPIECE):
            print(f"  {path.name}: {path.stat().st_size / 1024:.1f} KB")

    if render_sheets:
        if MASTERPIECE.is_file():
            print("Rendering the masterpiece contact sheet...", flush=True)
            sheet = render_contact_sheet(MASTERPIECE, MASTERPIECE_CONTACT_SHEET)
            print(f"  {sheet.name}: {sheet.stat().st_size / 1024:.1f} KB")
        if MASTERPIECE_TRAILER.is_file():
            print("Rendering the trailer contact sheet...", flush=True)
            sheet = render_contact_sheet(
                MASTERPIECE_TRAILER,
                MASTERPIECE_TRAILER_CONTACT_SHEET,
                frames=8,
                columns=4,
                rows=2,
                frame_width=270,
            )
            print(f"  {sheet.name}: {sheet.stat().st_size / 1024:.1f} KB")

    if render_clean:
        print("Rendering the clean 4:5 alternates...", flush=True)
        if args.clean or args.cut:
            cut = render_directors_cut(video)
            print(
                f"  {cut.name}: {cut.stat().st_size / (1024 * 1024):.1f} MB"
            )
        if args.clean or args.trailer:
            trailer = render_story_trailer(video)
            print(
                f"  {trailer.name}: {trailer.stat().st_size / (1024 * 1024):.1f} MB"
            )

    print("Done. Outputs are in:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
