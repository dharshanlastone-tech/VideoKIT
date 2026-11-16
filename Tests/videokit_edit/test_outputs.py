"""Integration checks for rendered files; skipped until outputs exist."""

from __future__ import annotations

import unittest

from videokit import Video

from edit_plan import (
    CLEAN_HEIGHT,
    CLEAN_WIDTH,
    DIRECTORS_CROSSFADE,
    DIRECTORS_CUT,
    DIRECTORS_CUT_SCENES,
    FPS,
    HEIGHT,
    MASTERPIECE,
    MASTERPIECE_CROSSFADE,
    MASTERPIECE_SCENES,
    MASTERPIECE_TRAILER,
    MASTERPIECE_TRAILER_CROSSFADE,
    MASTERPIECE_TRAILER_SCENES,
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


@unittest.skipUnless(DIRECTORS_CUT.is_file(), "run edit_video.py --cut first")
class DirectorsCutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.video = Video(DIRECTORS_CUT)

    def test_resolution(self):
        self.assertEqual(
            (self.video.width, self.video.height), (CLEAN_WIDTH, CLEAN_HEIGHT)
        )

    def test_frame_rate(self):
        self.assertAlmostEqual(self.video.fps, FPS, delta=0.01)

    def test_codec_and_audio(self):
        self.assertEqual(self.video.codec, "h264")
        self.assertTrue(self.video.has_audio)

    def test_duration_accounts_for_crossfades(self):
        expected = timeline_duration(DIRECTORS_CUT_SCENES, DIRECTORS_CROSSFADE)
        self.assertAlmostEqual(self.video.duration, expected, delta=1.0)


@unittest.skipUnless(STORY_TRAILER.is_file(), "run edit_video.py --trailer first")
class StoryTrailerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.video = Video(STORY_TRAILER)

    def test_resolution(self):
        self.assertEqual(
            (self.video.width, self.video.height), (CLEAN_WIDTH, CLEAN_HEIGHT)
        )

    def test_frame_rate(self):
        self.assertAlmostEqual(self.video.fps, FPS, delta=0.01)

    def test_codec_and_audio(self):
        self.assertEqual(self.video.codec, "h264")
        self.assertTrue(self.video.has_audio)

    def test_duration(self):
        expected = timeline_duration(STORY_TRAILER_SCENES, TRAILER_CROSSFADE)
        self.assertAlmostEqual(self.video.duration, expected, delta=1.0)


@unittest.skipUnless(MASTERPIECE.is_file(), "run edit_video.py --masterpiece first")
class MasterpieceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.video = Video(MASTERPIECE)

    def test_resolution_is_true_vertical(self):
        self.assertEqual((self.video.width, self.video.height), (WIDTH, HEIGHT))

    def test_frame_rate(self):
        # A 4-minute timeline can round to 29.98 fps in avg_frame_rate metadata.
        self.assertAlmostEqual(self.video.fps, FPS, delta=0.05)

    def test_codec_and_audio(self):
        self.assertEqual(self.video.codec, "h264")
        self.assertTrue(self.video.has_audio)

    def test_duration_accounts_for_speed_and_crossfades(self):
        expected = timeline_duration(MASTERPIECE_SCENES, MASTERPIECE_CROSSFADE)
        self.assertAlmostEqual(self.video.duration, expected, delta=1.5)

    def test_full_story_is_kept(self):
        self.assertGreater(self.video.duration, 200)
        self.assertLess(self.video.duration, SOURCE_DURATION)


@unittest.skipUnless(
    MASTERPIECE_TRAILER.is_file(), "run edit_video.py --masterpiece-trailer first"
)
class MasterpieceTrailerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.video = Video(MASTERPIECE_TRAILER)

    def test_resolution_is_true_vertical(self):
        self.assertEqual((self.video.width, self.video.height), (WIDTH, HEIGHT))

    def test_frame_rate(self):
        self.assertAlmostEqual(self.video.fps, FPS, delta=0.01)

    def test_codec_and_audio(self):
        self.assertEqual(self.video.codec, "h264")
        self.assertTrue(self.video.has_audio)

    def test_duration(self):
        expected = timeline_duration(
            MASTERPIECE_TRAILER_SCENES,
            MASTERPIECE_TRAILER_CROSSFADE,
        )
        self.assertAlmostEqual(self.video.duration, expected, delta=1.0)

    def test_trailer_is_short_enough_and_shorter_than_the_full_cut(self):
        self.assertLess(self.video.duration, 60)
        if not MASTERPIECE.is_file():
            self.skipTest("masterpiece is not rendered")
        self.assertLess(self.video.duration, Video(MASTERPIECE).duration)


@unittest.skipUnless(POSTER.is_file() and THUMBNAIL.is_file(), "run edit_video.py first")
class StillImageTests(unittest.TestCase):
    def test_poster_and_thumbnail_are_nonempty(self):
        for path in (POSTER, THUMBNAIL):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 5_000)


if __name__ == "__main__":
    unittest.main()
