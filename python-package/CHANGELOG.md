# Changelog

## 0.1.1

- Fix `clip.rotate()` so its output frame uses the rotation angle when
  calculating `rotw()`/`roth()` dimensions.
- Add `clip.tilt()` for smooth, animated rotation beats.
- Correct the speed documentation to note that audio tempo changes while pitch
  is preserved.

## 0.1.0

- Add video and audio metadata inspection.
- Add non-destructive video and audio time-range selection.
- Add video transforms, color adjustments, and fades.
- Add audio speed and volume controls.
- Add frame extraction.
- Add sequential timelines with audio mixing and crossfades.
- Add the JSON API description helper used by the VS Code extension.
