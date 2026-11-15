# VideoKit

[![PyPI](https://img.shields.io/pypi/v/videokit.svg)](https://pypi.org/project/videokit/)
[![Python versions](https://img.shields.io/pypi/pyversions/videokit.svg)](https://pypi.org/project/videokit/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/dharshanlastone-tech/VideoKIT/blob/main/python-package/LICENSE)

[GitHub repository](https://github.com/dharshanlastone-tech/VideoKIT) ·
[VS Code extension](https://marketplace.visualstudio.com/items?itemName=dharshanlastone-tech.videokit)

VideoKit is a small Python library for common video-editing tasks. It lets you
inspect a media file, describe edits in Python, and use FFmpeg to render the
result. Edits are non-destructive: methods such as `cut()`, `speed()`, and
`fade_in()` return new clip descriptions and leave your source files alone.

The package works on its own. The optional VS Code extension reads the installed
package's API to provide completions, hover documentation, signature help,
snippets, and video-path previews. It does not render video.

## What works today

- Read video and audio duration, video size, frame rate, and codec information.
- Select a time range from video or audio.
- Export a video cut accurately by default, or stream-copy it quickly.
- Convert a video to 9:16 portrait or 16:9 landscape framing.
- Choose draft, balanced, or high quality for final timeline renders.
- Change clip playback speed.
- Rotate a clip for a selected time interval.
- Resize and crop, flip, and adjust brightness, contrast, and saturation.
- Convert video to grayscale.
- Fade a clip's picture and audio in or out.
- Extract a still frame and make a bounded-size thumbnail.
- Adjust audio volume and speed, add audio fades, and export audio.
- Arrange video clips on a sequential timeline, using direct cuts or crossfades.
- Add positioned audio tracks to a timeline.

There is no standalone graphical editor. Audio pitch correction, text and image
overlays, and arbitrary clip positioning are not currently implemented. The
separate VS Code extension provides API-aware coding help and video previews;
it does not render video.

## Find what you need

- [Install](#install)
- [VS Code extension](#vs-code-extension)
- [Quick start](#quick-start)
- [Choose your workflow](#choose-your-workflow)
- [Inspect a video](#video-metadata)
- [Edit a clip](#cut-edit-and-export-a-clip)
- [Convert between portrait and landscape](#convert-between-portrait-and-landscape)
- [Choose final-render quality](#final-render-quality)
- [Extract frames and thumbnails](#extract-a-frame)
- [Edit audio](#audio-editing)
- [Join clips and mix audio](#timeline-cuts-and-crossfades)
- [Errors and quality notes](#errors-and-validation)
- [Current API limits](#public-api-and-current-limits)

## Requirements

- Python 3.10 or newer
- FFmpeg **and** FFprobe installed and available on `PATH`

VideoKit has no mandatory Python runtime dependencies. FFmpeg is a separate
program; VideoKit does not download or bundle it. Check your installation from
a terminal with `ffmpeg -version` and `ffprobe -version`. If either tool is
missing, VideoKit raises `FFmpegError` with installation guidance.

The package is licensed under MIT; see
[LICENSE](https://github.com/dharshanlastone-tech/VideoKIT/blob/main/python-package/LICENSE).

## Install

```powershell
python -m pip install videokit
```

VideoKit has no mandatory Python runtime dependencies. Install FFmpeg and
FFprobe separately and confirm that both commands work in your terminal.

To work on a local checkout instead, open a terminal in `python-package` and
run:

```powershell
python -m pip install -e .
```

## VS Code extension

The optional extension is published as
`dharshanlastone-tech.videokit`. Install it from the
[Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=dharshanlastone-tech.videokit),
from the Extensions view in VS Code, or with:

```powershell
code --install-extension dharshanlastone-tech.videokit
```

Select the Python environment that has VideoKit installed to enable its
API-aware features. The extension is purely an editing aid; it does not replace
the Python package or FFmpeg.

## Quick start

```python
from videokit import Video

video = Video("movie.mp4")
print(f"Duration: {video.duration:.2f} seconds")
print(f"Size: {video.width} x {video.height}")
print(f"Frame rate: {video.fps}")
print(f"Video codec: {video.codec}")
print(f"Has audio: {video.has_audio}")

scene = video.cut(5, 15)
scene.export("scene.mp4")
```

All time values are seconds. Paths can be strings or `pathlib.Path` objects.
`Video` resolves the path and reads actual stream metadata with FFprobe; missing
or invalid media is reported instead of filled with guessed values.

## Choose your workflow

| What you want to do | Start here |
| --- | --- |
| Read a video's size or duration | `video = Video("input.mp4")` |
| Save one section | `video.cut(start, end).export("clip.mp4")` |
| Edit speed, color, framing, or fades | Chain methods on `video.cut(start, end)` |
| Make a portrait/social video | `video.to_vertical().export("portrait.mp4")` |
| Make a landscape video | `video.to_horizontal().export("landscape.mp4")` |
| Join clips or add music | `Timeline()` then `.render("final.mp4")` |
| Make an image preview | `video.thumbnail("preview.jpg")` |

For best-quality final output, use `quality="high"` when rendering a timeline.
For fast drafts, use `quality="draft"`.

## Video metadata

```python
from videokit import Video

video = Video("movie.mp4")

video.path        # absolute source path
video.duration    # seconds
video.width       # pixels
video.height      # pixels
video.resolution  # (width, height)
video.fps         # frames per second, or None if FFprobe has no usable rate
video.codec       # FFmpeg codec name, or None if unavailable
video.has_audio   # whether the file has an audio stream
```

## Cut, edit, and export a clip

`cut(start, end)` selects the half-open interval from `start` up to (but not
including) `end`. The range must be positive and within the source duration.
Editing calls can be chained; each returns a new `Clip`.

```python
from videokit import Video

video = Video("movie.mp4")
clip = (
    video.cut(5, 15)
    .speed(1.25)
    .resize(1280, 720)
    .brightness(0.05)
    .fade_in(0.5)
    .fade_out(1.0)
)
print(clip.duration)  # 8 seconds after the speed change
clip.export("scene.mp4")
```

`Clip.export()` re-encodes by default so cuts and edits can be honored at the
requested timestamps. The default output video codec is H.264 and audio is AAC.
For an unedited cut, `clip.export("scene.mp4", accurate=False)` uses stream
copying for speed; most codecs can only cut at nearby keyframes in that mode.
Once a clip has edits, VideoKit encodes it even if `accurate=False`.

Outputs are not overwritten by default. Pass `overwrite=True` to replace an
existing output file.

## Convert between portrait and landscape

Use the convenience methods directly on a `Video`, or on a selected `Clip`.
Both methods return a clip you can continue editing and export:

```python
from videokit import Video

video = Video("wide-video.mp4")

# Make a vertical 9:16 video (default 1080 x 1920).
portrait = video.to_vertical()
portrait.export("portrait.mp4")

# Convert that clip back to a horizontal 16:9 video.
landscape = portrait.to_horizontal()
landscape.export("landscape.mp4")
```

By default, conversion **fills the new frame** (`mode="crop"`). This produces
the requested aspect ratio without bars, but part of the original picture must
be cropped. For a 16:9-to-9:16 conversion, the default crop is centered.
Choose a different crop focus when the subject is not centered:

```python
# Keep a subject closer to the right side of the original landscape frame.
portrait = video.to_vertical(focus_x=0.75)
portrait.export("portrait-focused.mp4")
```

`focus_x` and `focus_y` are positions from `0` to `1`: `0` favors the left or
top edge, `0.5` centers the crop, and `1` favors the right or bottom edge.
These settings choose where the crop is anchored; they do not track a moving
subject.

If you want to keep **all** of the original picture instead, use `mode="fit"`.
VideoKit adds black bars where needed:

```python
portrait_with_bars = video.to_vertical(mode="fit")
portrait_with_bars.export("portrait-full-picture.mp4")
```

Output size defaults to `1080 x 1920` for portrait and `1920 x 1080` for
landscape. You can choose a smaller even-sized output for faster renders:

```python
portrait_720p = video.to_vertical(width=720, height=1280)
landscape_720p = portrait_720p.to_horizontal(width=1280, height=720)
```

Dimensions must match the requested ratio and be even integers. Reframing is
performed at render time and does not alter the source video.

## Final render quality

Use `Timeline.render()` for a clear final-output step. It renders all timeline
clips, crossfades, and audio tracks into one H.264/AAC video:

```python
from videokit import Audio, RenderSettings, Timeline, Video

timeline = Timeline()
timeline.add(Video("intro.mp4").cut(0, 5))
timeline.add(Video("main.mp4").cut(2, 20), crossfade=0.75)
timeline.add_audio(Audio("music.mp3").cut(0, 22).volume(0.2))

# Simple option:
timeline.render("final.mp4", quality="high")

# Or reuse an explicit settings object:
settings = RenderSettings(quality="balanced")
timeline.export("review.mp4", settings=settings)
```

| Quality | FFmpeg preset | CRF | Best for |
| --- | --- | --- | --- |
| `"draft"` | `veryfast` | 28 | Quick checks and rough drafts |
| `"balanced"` | `medium` | 22 | Everyday output (default) |
| `"high"` | `slow` | 18 | Higher image quality; takes longer and usually creates larger files |

CRF is FFmpeg's quality scale: lower numbers preserve more image detail and
usually produce larger files. The settings use H.264 video and 192 kb/s AAC
audio. For individual edited clips, pass the same settings to `Clip.export()`:
`clip.export("scene.mp4", settings=RenderSettings(quality="high"))`.
`Timeline.export()` remains available; it accepts `settings=...` and continues
to accept the output size and frame rate options.

Rendering involves encoding the complete result, so it takes longer than
stream-copying an unedited clip. For a fast preview, use `quality="draft"`; for
the final delivery, choose `"balanced"` or `"high"` based on your needs.

### Clip operations

| Method | Behavior |
| --- | --- |
| `clip.speed(factor)` | Multiply playback speed. `2` is twice as fast; `0.5` is half speed. Audio pitch changes with speed. |
| `clip.rotate(degrees, start=0, end=None)` | Rotate clockwise during a time interval relative to the clip's playback. Exposed pixels are black. |
| `clip.resize(width, height)` | Fit inside the requested even-sized frame and pad unused space with black; aspect ratio is preserved. |
| `clip.to_vertical(...)` / `clip.to_horizontal(...)` | Reframe to 9:16 portrait or 16:9 landscape using centered cropping or black-bar fitting. |
| `clip.crop(width, height, x=0, y=0)` | Crop an even-sized pixel rectangle from the current frame. |
| `clip.flip(horizontal=False, vertical=False)` | Flip one or both directions; at least one direction must be enabled. |
| `clip.brightness(amount)` | Set brightness in the range `-1` to `1`; `0` is unchanged. |
| `clip.contrast(amount)` | Set contrast in the range `0` to `4`; `1` is unchanged. |
| `clip.saturation(amount)` | Set saturation in the range `0` to `3`; `1` is unchanged. |
| `clip.grayscale()` | Remove color. |
| `clip.fade_in(duration)` / `clip.fade_out(duration)` | Fade picture from/to black and audio from/to silence. |

For example, rotate a clip only from second 2 through second 4 of its playback:

```python
portrait = video.cut(0, 8).rotate(90, start=2, end=4)
portrait.export("portrait.mp4")
```

`rotate()` accepts any finite angle in degrees. Rotation can increase the output
frame dimensions to keep the rotated picture visible. Crop dimensions and
positions are checked against the original video size.

## Extract a frame

`extract_frame()` writes one still image and returns its absolute path. Choose
the image extension, for example `.png` or `.jpg`, in the output path.

```python
video = Video("movie.mp4")
thumbnail = video.extract_frame(3.5, "thumbnail.png")
small_preview = video.thumbnail("preview.jpg", max_width=320, max_height=180)
```

The timestamp must be inside the video. Frame decoding is done by FFmpeg; the
whole video is not loaded into Python memory.
`thumbnail()` defaults to the middle of the video and preserves aspect ratio
within the requested maximum dimensions.

## Audio editing

```python
from videokit import Audio

music = Audio("background.mp3")
print(music.duration, music.codec, music.sample_rate, music.channels)

intro = music.cut(0, 20).volume(0.35).fade_in(1).fade_out(2)
intro.export("intro.mp3")
```

| Method | Behavior |
| --- | --- |
| `audio.cut(start, end)` | Select a valid time range, returning an `AudioClip`. |
| `clip.volume(level)` | Set volume from `0` (silent) to `4` (four times the source level). |
| `clip.speed(factor)` | Change duration and pitch by changing playback speed. |
| `clip.fade_in(duration)` / `clip.fade_out(duration)` | Apply an audio fade. |
| `clip.export(path)` | Export as MP3 for `.mp3`, WAV for `.wav`, otherwise AAC. |

Audio re-encoding is required for precise cuts and processing. The selected
extension determines the output encoding; use `.mp3`, `.wav`, `.m4a`, or another
format supported by the installed FFmpeg build.

## Timeline, cuts, and crossfades

Add video clips in playback order. Consecutive clips meet with a direct cut by
default; `crossfade` specifies the overlap with the preceding clip in seconds.
The first clip cannot have a crossfade.

```python
from videokit import Audio, Timeline, Video

first_video = Video("first.mp4")
second_video = Video("second.mp4")

timeline = Timeline()
timeline.add(first_video.cut(0, 8))
timeline.add(second_video.cut(2, 10), crossfade=1.0)

music = Audio("music.mp3").cut(0, 16).volume(0.2).fade_in(1)
timeline.add_audio(music, at=0)

print(timeline.duration)
timeline.export("finished.mp4")
```

The output uses the first video clip's dimensions and frame rate by default.
Clips with differing dimensions are fitted and padded to that size. If the
first clip has no usable frame rate, timeline export uses 30 fps. You can set
the output explicitly:

```python
timeline.export("finished.mp4", width=1920, height=1080, fps=30)
```

Width and height must be even integers of at least two pixels. Video from each
clip is encoded as H.264; audio is mixed and encoded as AAC. Clips without
source audio contribute silence, so music remains synchronized through cuts and
crossfades. Audio added with `add_audio()` starts at the `at` position and is
mixed with any source audio.

## Errors and validation

- `MediaError`: missing or unreadable media, missing media streams, or invalid
  required metadata.
- `FFmpegError`: FFmpeg/FFprobe is unavailable or the requested media operation
  fails. The FFmpeg error output is included to help diagnose codec issues.
- `ValueError`: invalid timestamps, dimensions, speed, effects, or output
  settings.
- `FileExistsError`: output already exists and `overwrite=True` was not set.

FFmpeg filter availability and media codec support depend on the FFmpeg build
installed on your computer. VideoKit surfaces FFmpeg failures rather than
pretending an unsupported operation succeeded.

## Performance and quality

- Metadata and frame extraction are delegated to FFprobe/FFmpeg.
- Video and audio files are not read wholly into Python memory.
- Stream-copy exports are fast and avoid generation loss, but cuts may be
  keyframe-aligned rather than frame-exact.
- Accurate cuts, visual edits, speed changes, and timeline composition encode
  media and take longer. Timeline export uses the selected `RenderSettings`
  quality preset; the default `balanced` preset is H.264 `medium` with CRF 22
  and 192 kb/s AAC audio.
- Changing playback speed also changes audio pitch. Pitch-preserving
  time-stretching is not implemented.
- `crossfade` blends picture and audio for the selected overlap. Other
  transition styles are not implemented yet.

## Public API and current limits

Import supported types from `videokit`: `Video`, `Clip`, `Audio`, `AudioClip`,
and `Timeline`. The package also exports `VideoKitError`, `MediaError`, and
`FFmpegError`.

There is currently no image overlay, text rendering, general-purpose visual
effect plug-in API, arbitrary timeline positioning of video clips, cancellation
interface, or GUI. The separate VS Code extension provides coding assistance and
previews; it is not a renderer. New features should be added only with a
well-defined API and matching implementation/documentation.

## Development

Run the package's focused tests from this directory:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

The tests cover metadata parsing, validation, reframing, render presets, and the
VS Code helper. For media output, also try the examples above with a local
FFmpeg installation and representative files from the codecs you expect to use.
