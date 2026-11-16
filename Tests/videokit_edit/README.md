# VideoKit test edit: *Mira and Twinkle*

This folder turns the local story video `Tests/Untitled Project.mp4` into a
finished vertical film using the **VideoKit** Python package. The source file is
never modified.

The source is a 1080x1350 4:5 canvas with a 9:16 illustration pillarboxed inside
it. The main edit crops that baked-in border away and delivers a true
1080x1920 vertical film with speed ramps, contrast pulses, smooth tilt beats,
crossfades, and fades.

## Main outputs

| File | What it is |
| --- | --- |
| `output/videokit_masterpiece.mp4` | The full 4:02 effects cut: 1080x1920, 30 fps, H.264/AAC, with speed ramps, contrast/saturation grades, six animated tilt beats, crossfades, and fades. |
| `output/videokit_masterpiece_trailer.mp4` | A 48-second vertical trailer made from sentence-complete story moments and the strongest tilt beats. |
| `output/videokit_poster.jpg` | Vertical poster frame from the glow scene. |
| `output/videokit_thumbnail.jpg` | Small 9:16 thumbnail from the final village scene. |
| `output/masterpiece_contact_sheet.jpg` | 12-frame overview of the full effects cut. |
| `output/masterpiece_trailer_contact_sheet.jpg` | 8-frame overview of the vertical trailer. |
| `output/edit_plan.json` | Every source range, speed, grade value, tilt, zoom, crossfade, and expected duration. |
| `output/preview.html` | A local browser page that plays the vertical cut and trailer. |

The clean 4:5 alternates are still available:

| File | What it is |
| --- | --- |
| `output/videokit_directors_cut.mp4` | The complete 4:13 clean story at 1080x1350 with a subtle warm grade and soft transitions. |
| `output/videokit_story_trailer.mp4` | The 47-second clean 4:5 trailer. |

Open the preview page after rendering:

```powershell
start .\Tests\videokit_edit\output\preview.html
```

## Code

- `edit_plan.py` — source ranges, speed/grade/tilt settings, 9:16 output
  settings, validation, and timeline-duration math.
- `edit_video.py` — builds the timelines, applies VideoKit effects, renders the
  videos, extracts stills, and creates contact sheets.
- `test_edit_plan.py` — fast tests for scene ranges, effects, crossfades, tilt
  safety, and durations.
- `test_outputs.py` — integration checks for the rendered videos and stills.
- `run_edit.ps1` — install, test, render, and verify in one command.

The core of the effects pipeline:

```python
from videokit import RenderSettings, Timeline, Video

video = Video("Tests/Untitled Project.mp4")
clip = video.cut(35.6, 41.88)

# Remove the baked-in pillarbox and reframe as true 9:16.
clip = clip.crop(752, 1350, x=164, y=0)
clip = clip.speed(1.15).contrast(1.22).saturation(1.22)
clip = clip.to_vertical(width=1080, height=1920, mode="crop")

# Punch in, upscale, animate a smooth tilt, then crop back to 1080x1920.
clip = clip.crop(864, 1536, x=108, y=192)
clip = clip.resize(1404, 2496)
clip = clip.tilt(6, from_degrees=0)
clip = clip.crop(1080, 1920, x=289, y=355)

timeline = Timeline()
timeline.add(clip)
timeline.export(
    "output/videokit_masterpiece.mp4",
    width=1080,
    height=1920,
    fps=30,
    settings=RenderSettings(quality="high"),
    overwrite=True,
)
```

The production code computes the tilt crop and final crop from the clip's
rotated frame size, so the example above uses the same idea with one concrete
scene's numbers.

## Run it

From the repository root:

```powershell
python -m pip install -e .\python-package
python .\Tests\videokit_edit\edit_video.py
```

The default run renders the vertical masterpiece, the vertical trailer, the
poster/thumbnail, and the contact sheets.

Render only one deliverable:

```powershell
python .\Tests\videokit_edit\edit_video.py --masterpiece
python .\Tests\videokit_edit\edit_video.py --masterpiece-trailer
python .\Tests\videokit_edit\edit_video.py --stills
```

Render the clean 4:5 alternates:

```powershell
python .\Tests\videokit_edit\edit_video.py --cut
python .\Tests\videokit_edit\edit_video.py --trailer
python .\Tests\videokit_edit\edit_video.py --clean
```

Or run the complete workflow:

```powershell
.\Tests\videokit_edit\run_edit.ps1
```

The script uses FFmpeg and FFprobe from `PATH`. The high-quality effects cut
takes several minutes; the trailer is much faster.

## Test it

```powershell
python -m unittest discover -s .\Tests\videokit_edit -p "test_edit_plan.py" -v
python -m unittest discover -s .\Tests\videokit_edit -p "test_outputs.py" -v
```

The output tests are skipped automatically until the videos have been rendered.

The package itself also has tests:

```powershell
python -m unittest discover -s .\python-package\tests -p "test_*.py" -v
```

## Edit decisions

The source has hard scene changes at about 27.6, 75.2, 203.9, and 241.0 s. The
masterpiece:

1. Keeps the complete story, including the final subscribe card.
2. Crops the 752x1350 illustration out of the 1080x1350 canvas and reframes it
   as true 1080x1920 vertical.
3. Speed-ramps the story: 1.22x for the energetic physics section, 0.85x for
   the glow beat, and 0.9x for the quiet listening section.
4. Adds a per-scene contrast/saturation grade, with the strongest grade on the
   glow beat.
5. Uses six animated tilt beats. Each one punches in 1.15-1.30x, upscales to
   a safe intermediate frame, animates a 3-7 degree tilt with
   `Clip.tilt()`, then crops back to 1080x1920 with no black corners.
6. Uses hard cuts at effect boundaries so the narration stays seamless, and
   short crossfades where the story has a natural pause.
7. Fades in from black and out at the end.

The vertical trailer uses only sentence-complete narration ranges, so no line
is cut in the middle. It ends before the final subscribe card.

## Note about the source file

`Tests/Untitled Project.mp4` is a local 112 MB source video and is not committed
to Git. The edit code, tests, README, poster, thumbnail, contact sheets, and
preview page are small enough to commit; the rendered videos are ignored by
`.gitignore` to keep the repository light.
