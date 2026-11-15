"""Integration checks for rendered files; skipped until outputs exist."""

from __future__ import annotations

import unittest

from videokit import Video

from edit_plan import (
    DIRECTORS_CROSSFADE,
    DIRECTORS_CUT,
    DIRECTORS_CUT_SCENES,
    FPS,
    HEIGHT,
    POSTER,
    SOURCE,
    SOURCE_DURATION,
    STORY_TRAILER,
    STORY_TRAILER_SCENES,
    THUMBNAIL,
    TRAILER_CROSSFADE,
    WIDTH,
    timeline_duration,
)


@unittest.skipUnless(SOURCE.is_file(), "local source video is not present")
class SourceVideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.video = Video(SOURCE)

    def test_source_is_vertical_story_frame(self):
        self.assertEqual((self.video.width, self.video.height), (1080, 1350))
        self.assertTrue(self.video.has_audio)

    def test_plan_matches_source_duration(self):
        self.assertAlmostEqual(self.video.duration, SOURCE_DURATION, delta=0.1)


@unittest.skipUnless(DIRECTORS_CUT.is_file(), "run edit_video.py first")
class DirectorsCutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.video = Video(DIRECTORS_CUT)

    def test_resolution(self):
        self.assertEqual((self.video.width, self.video.height), (WIDTH, HEIGHT))

    def test_frame_rate(self):
        self.assertAlmostEqual(self.video.fps, FPS, delta=0.01)

    def test_codec_and_audio(self):
        self.assertEqual(self.video.codec, "h264")
        self.assertTrue(self.video.has_audio)

    def test_duration_accounts_for_crossfades(self):
        expected = timeline_duration(DIRECTORS_CUT_SCENES, DIRECTORS_CROSSFADE)
        self.assertAlmostEqual(self.video.duration, expected, delta=1.0)


@unittest.skipUnless(STORY_TRAILER.is_file(), "run edit_video.py first")
class StoryTrailerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.video = Video(STORY_TRAILER)

    def test_resolution(self):
        self.assertEqual((self.video.width, self.video.height), (WIDTH, HEIGHT))

    def test_frame_rate(self):
        self.assertAlmostEqual(self.video.fps, FPS, delta=0.01)

    def test_codec_and_audio(self):
        self.assertEqual(self.video.codec, "h264")
        self.assertTrue(self.video.has_audio)

    def test_duration(self):
        expected = timeline_duration(STORY_TRAILER_SCENES, TRAILER_CROSSFADE)
        self.assertAlmostEqual(self.video.duration, expected, delta=1.0)

    def test_trailer_is_shorter_than_the_full_cut(self):
        if not DIRECTORS_CUT.is_file():
            self.skipTest("director's cut is not rendered")
        self.assertLess(self.video.duration, Video(DIRECTORS_CUT).duration)


@unittest.skipUnless(POSTER.is_file() and THUMBNAIL.is_file(), "run edit_video.py first")
class StillImageTests(unittest.TestCase):
    def test_poster_and_thumbnail_are_nonempty(self):
        for path in (POSTER, THUMBNAIL):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 5_000)


if __name__ == "__main__":
    unittest.main()
