"""Fast unit tests for the edit decisions; no FFmpeg render is required."""

from __future__ import annotations

import unittest

from edit_plan import (
    DIRECTORS_CROSSFADE,
    DIRECTORS_CUT_SCENES,
    FPS,
    HEIGHT,
    SOURCE_DURATION,
    STORY_TRAILER_SCENES,
    TRAILER_CROSSFADE,
    WIDTH,
    timeline_duration,
    validate_scenes,
)


class EditPlanTests(unittest.TestCase):
    def test_directors_cut_scenes_are_valid(self):
        validate_scenes(
            DIRECTORS_CUT_SCENES,
            duration=SOURCE_DURATION,
            crossfade=DIRECTORS_CROSSFADE,
        )

    def test_story_trailer_scenes_are_valid(self):
        validate_scenes(
            STORY_TRAILER_SCENES,
            duration=SOURCE_DURATION,
            crossfade=TRAILER_CROSSFADE,
        )

    def test_scenes_are_in_order_and_do_not_overlap(self):
        for scenes in (DIRECTORS_CUT_SCENES, STORY_TRAILER_SCENES):
            for earlier, later in zip(scenes, scenes[1:]):
                self.assertLessEqual(earlier.end, later.start)

    def test_crossfade_is_shorter_than_every_scene(self):
        for scenes, crossfade in (
            (DIRECTORS_CUT_SCENES, DIRECTORS_CROSSFADE),
            (STORY_TRAILER_SCENES, TRAILER_CROSSFADE),
        ):
            for scene in scenes:
                self.assertLess(crossfade, scene.duration)

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

    def test_trailer_is_short_enough_to_share(self):
        self.assertLess(
            timeline_duration(STORY_TRAILER_SCENES, TRAILER_CROSSFADE), 60
        )

    def test_output_settings_are_valid(self):
        self.assertEqual((WIDTH, HEIGHT), (1080, 1350))
        self.assertEqual(WIDTH % 2, 0)
        self.assertEqual(HEIGHT % 2, 0)
        self.assertEqual(FPS, 30)

    def test_scene_titles_are_unique(self):
        for scenes in (DIRECTORS_CUT_SCENES, STORY_TRAILER_SCENES):
            titles = [scene.title for scene in scenes]
            self.assertEqual(len(titles), len(set(titles)))

    def test_invalid_scenes_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_scenes((), crossfade=0)
        with self.assertRaises(ValueError):
            validate_scenes(DIRECTORS_CUT_SCENES, crossfade=30)
        with self.assertRaises(ValueError):
            validate_scenes(DIRECTORS_CUT_SCENES, duration=100, crossfade=0)


if __name__ == "__main__":
    unittest.main()
