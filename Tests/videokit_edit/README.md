# VideoKit test edit: *Mira and Twinkle*

This folder turns the local story video `Tests/Untitled Project.mp4` into two
finished cuts using the published **VideoKit** Python package. The source file
is never modified.

## Outputs

| File | What it is |
| --- | --- |
| `output/videokit_directors_cut.mp4` | The complete 4:13 story at 1080×1350, 30 fps, H.264/AAC, with a subtle warm grade, soft scene transitions, and opening/closing fades. |
| `output/videokit_story_trailer.mp4` | A 47-second, sentence-complete retelling for quick sharing. |
| `output/videokit_poster.jpg` | Poster frame from the moment Twinkle glows in Mira's hands. |
| `output/videokit_thumbnail.jpg` | Small 4:5 thumbnail from the final village scene. |
| `output/edit_plan.json` | Every scene range, crossfade, grade value, and expected duration. |
| `output/directors_cut_contact_sheet.jpg` | 15-frame overview of the full cut. |
| `output/trailer_contact_sheet.jpg` | 12-frame overview of the trailer. |
| `output/preview.html` | A local browser page that plays both cuts side by side. |

Open the preview page after rendering:

```powershell
start .\Tests\videokit_edit\output\preview.html
```

## Code

- `edit_plan.py` — scene ranges, grade settings, output settings, validation.
- `edit_video.py` — builds the timelines and renders the outputs with VideoKit.
- `test_edit_plan.py` — fast tests for scene ranges, crossfades, and durations.
- `test_outputs.py` — integration checks for the rendered video and still files.
- `run_edit.ps1` — install, test, render, and verify in one command.

The main pipeline is intentionally small:

```python
video = Video(SOURCE)
timeline = Timeline()
for scene in scenes:
    clip = (
        video.cut(scene.start, scene.end)
        .brightness(0.015)
        .contrast(1.08)
        .saturation(1.12)
    )
    timeline.add(clip, crossfade=0.45)
timeline.export(
    "output/videokit_directors_cut.mp4",
    width=1080,
    height=1350,
    fps=30,
    settings=RenderSettings(quality="high"),
    overwrite=True,
)
```

## Run it

From the repository root:

```powershell
python -m pip install -e .\python-package
python .\Tests\videokit_edit\edit_video.py
```

Or render only the parts you need:

```powershell
python .\Tests\videokit_edit\edit_video.py --stills --trailer
python .\Tests\videokit_edit\edit_video.py --cut
```

Or run the complete workflow:

```powershell
.\Tests\videokit_edit\run_edit.ps1
```

The script uses FFmpeg and FFprobe from `PATH`. Rendering the full 4-minute
high-quality cut can take several minutes; the trailer is much faster.

## Test it

```powershell
python -m unittest discover -s .\Tests\videokit_edit -p "test_edit_plan.py" -v
python -m unittest discover -s .\Tests\videokit_edit -p "test_outputs.py" -v
```

The output tests are skipped automatically until the videos have been rendered.

## Edit decisions

The source is a 1080×1350, 60 fps illustrated story with narration. The cut:

1. Keeps the complete story, including the final message.
2. Splits at the detected scene changes (about 27.6, 75.2, 203.9, and 241.0 s).
3. Uses 0.45-second crossfades so hard scene changes feel gentler.
4. Adds a restrained brightness/contrast/saturation grade so the illustrations
   pop without looking oversaturated.
5. Fades in from black and out at the end.
6. Renders at 30 fps for a calmer, more cinematic feel and a smaller file.

The 47-second trailer only uses sentence-complete narration ranges, so no line
is cut in the middle.

## Note about the source file

`Tests/Untitled Project.mp4` is a local 112 MB source video and is not committed
to Git. The edit code, tests, README, poster, and thumbnail are small enough to
commit; the rendered videos are ignored by `.gitignore` to keep the repository
light.
