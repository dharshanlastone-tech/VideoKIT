"""Fast unit tests for the edit decisions; no FFmpeg render is required."""

from __future__ import annotations

import unittest

from edit_plan import (
    ARTWORK_HEIGHT,
    ARTWORK_WIDTH,
    ARTWORK_X,
    CLEAN_HEIGHT,
    CLEAN_WIDTH,
    DIRECTORS_CROSSFADE,
    DIRECTORS_CUT_SCENES,
    FPS,
    HEIGHT,
    MASTERPIECE_CROSSFADE,
    MASTERPIECE_SCENES,
    MASTERPIECE_TRAILER_CROSSFADE,
    MASTERPIECE_TRAILER_SCENES,
    MAX_TILT_DEGREES,
    SOURCE_DURATION,
    STORY_TRAILER_SCENES,
    TILT_FRAME_SCALE,
    TRAILER_CROSSFADE,
    WIDTH,
    required_tilt_scale,
    scene_start,
    timeline_duration,
    validate_scenes,
)


class EditPlanTests(unittest.TestCase):
    def test_every_edit_plan_is_valid(self):
        for scenes, crossfade in (
            (DIRECTORS_CUT_SCENES, DIRECTORS_CROSSFADE),
            (STORY_TRAILER_SCENES, TRAILER_CROSSFADE),
            (MASTERPIECE_SCENES, MASTERPIECE_CROSSFADE),
            (MASTERPIECE_TRAILER_SCENES, MASTERPIECE_TRAILER_CROSSFADE),
        ):
            validate_scenes(scenes, duration=SOURCE_DURATION, crossfade=crossfade)

    def test_scenes_are_in_order_and_do_not_overlap(self):
        for scenes in (
            DIRECTORS_CUT_SCENES,
            STORY_TRAILER_SCENES,
            MASTERPIECE_SCENES,
            MASTERPIECE_TRAILER_SCENES,
        ):
            for earlier, later in zip(scenes, scenes[1:]):
                self.assertLessEqual(earlier.end, later.start)

    def test_crossfade_is_shorter_than_every_scene(self):
        for scenes, crossfade in (
            (DIRECTORS_CUT_SCENES, DIRECTORS_CROSSFADE),
            (STORY_TRAILER_SCENES, TRAILER_CROSSFADE),
            (MASTERPIECE_SCENES, MASTERPIECE_CROSSFADE),
            (MASTERPIECE_TRAILER_SCENES, MASTERPIECE_TRAILER_CROSSFADE),
        ):
            for scene in scenes:
                chosen = crossfade if scene.crossfade is None else scene.crossfade
                self.assertLess(chosen, scene.playback_duration)

    def test_expected_timeline_durations(self):
        self.assertAlmostEqual(
            timeline_duration(DIRECTORS_CUT_SCENES, DIRECTORS_CROSSFADE),
            253.45,
            places=2,
        )
        self.assertAlmostEqual(
            timeline_duration(STORY_TRAILER_SCENES, TRAILER_CROSSFADE),
            47.44,
            places=2,
        )
        self.assertAlmostEqual(
            timeline_duration(MASTERPIECE_SCENES, MASTERPIECE_CROSSFADE),
            241.82,
            places=2,
        )
        self.assertAlmostEqual(
            timeline_duration(
                MASTERPIECE_TRAILER_SCENES,
                MASTERPIECE_TRAILER_CROSSFADE,
            ),
            47.71,
            places=2,
        )

    def test_trailers_are_short_enough_to_share(self):
        self.assertLess(
            timeline_duration(STORY_TRAILER_SCENES, TRAILER_CROSSFADE), 60
        )
        self.assertLess(
            timeline_duration(
                MASTERPIECE_TRAILER_SCENES,
                MASTERPIECE_TRAILER_CROSSFADE,
            ),
            60,
        )

    def test_output_settings_are_valid(self):
        self.assertEqual((WIDTH, HEIGHT), (1080, 1920))
        self.assertEqual((CLEAN_WIDTH, CLEAN_HEIGHT), (1080, 1350))
        self.assertEqual(WIDTH % 2, 0)
        self.assertEqual(HEIGHT % 2, 0)
        self.assertEqual(FPS, 30)

    def test_source_artwork_crop_fits_the_source_canvas(self):
        self.assertLessEqual(ARTWORK_X + ARTWORK_WIDTH, 1080)
        self.assertEqual(ARTWORK_HEIGHT, 1350)

    def test_masterpiece_uses_visible_effects_and_speed_ramps(self):
        tilt_scenes = [scene for scene in MASTERPIECE_SCENES if scene.has_tilt]
        self.assertGreaterEqual(len(tilt_scenes), 5)
        self.assertGreater(max(scene.speed for scene in MASTERPIECE_SCENES), 1.2)
        self.assertLess(min(scene.speed for scene in MASTERPIECE_SCENES), 0.95)
        self.assertGreater(
            max(scene.contrast for scene in MASTERPIECE_SCENES),
            max(scene.contrast for scene in DIRECTORS_CUT_SCENES),
        )

    def test_every_tilt_has_enough_frame_scale(self):
        for scenes in (MASTERPIECE_SCENES, MASTERPIECE_TRAILER_SCENES):
            for scene in scenes:
                if not scene.has_tilt:
                    continue
                largest = max(abs(scene.tilt), abs(scene.tilt_from))
                self.assertLessEqual(largest, MAX_TILT_DEGREES)
                self.assertGreaterEqual(
                    TILT_FRAME_SCALE,
                    required_tilt_scale(largest),
                )
                self.assertGreater(scene.zoom, 1)

    def test_scene_start_matches_the_crossfade_math(self):
        first = MASTERPIECE_SCENES[0]
        second = MASTERPIECE_SCENES[1]
        second_crossfade = (
            MASTERPIECE_CROSSFADE
            if second.crossfade is None
            else second.crossfade
        )
        self.assertAlmostEqual(
            scene_start(MASTERPIECE_SCENES, 0, MASTERPIECE_CROSSFADE), 0.0
        )
        self.assertAlmostEqual(
            scene_start(MASTERPIECE_SCENES, 1, MASTERPIECE_CROSSFADE),
            first.playback_duration - second_crossfade,
        )
        with self.assertRaises(IndexError):
            scene_start(MASTERPIECE_SCENES, len(MASTERPIECE_SCENES), 0)

    def test_scene_titles_are_unique(self):
        for scenes in (
            DIRECTORS_CUT_SCENES,
            STORY_TRAILER_SCENES,
            MASTERPIECE_SCENES,
            MASTERPIECE_TRAILER_SCENES,
        ):
            titles = [scene.title for scene in scenes]
            self.assertEqual(len(titles), len(set(titles)))

    def test_invalid_scenes_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_scenes((), crossfade=0)
        with self.assertRaises(ValueError):
            validate_scenes(DIRECTORS_CUT_SCENES, crossfade=30)
        with self.assertRaises(ValueError):
            validate_scenes(DIRECTORS_CUT_SCENES, duration=100, crossfade=0)
        with self.assertRaises(ValueError):
            validate_scenes(
                (MASTERPIECE_SCENES[0].__class__(0, 10, "bad speed", speed=0),),
                crossfade=0,
            )
        with self.assertRaises(ValueError):
            validate_scenes(
                (
                    MASTERPIECE_SCENES[0].__class__(
                        0,
                        10,
                        "too much tilt",
                        tilt=20,
                        zoom=1.25,
                    ),
                ),
                crossfade=0,
            )


if __name__ == "__main__":
    unittest.main()
