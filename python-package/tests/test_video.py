import unittest
from pathlib import Path
from unittest.mock import patch

from videokit import Clip, RenderSettings, Video
from videokit.exceptions import MediaError
from videokit._vscode import preview_at


class VideoTests(unittest.TestCase):
    def test_portrait_and_landscape_reframing(self):
        clip = Clip(Path("movie.mp4"), 0, 10, _width=1920, _height=1080)

        portrait = clip.to_vertical()
        landscape = portrait.to_horizontal()

        self.assertEqual((portrait._width, portrait._height), (1080, 1920))
        self.assertEqual((landscape._width, landscape._height), (1920, 1080))
        self.assertEqual(len(portrait._filters), 3)

    def test_fit_mode_and_invalid_aspect_ratio(self):
        clip = Clip(Path("movie.mp4"), 0, 10, _width=1920, _height=1080)

        fitted = clip.to_vertical(mode="fit")
        self.assertIn("color=black", fitted._filters[1])
        with self.assertRaises(ValueError):
            clip.to_vertical(width=720, height=720)
        with self.assertRaises(ValueError):
            clip.to_vertical(focus_x=2)

    def test_render_settings_have_explicit_quality_levels(self):
        self.assertEqual(RenderSettings("balanced").preset, "medium")
        self.assertEqual(RenderSettings("high").crf, 18)
        with self.assertRaises(ValueError):
            RenderSettings("ultra")

    def test_video_path_preview_only_matches_video_constructor_literal(self):
        source = (
            "from videokit import Video as VKVideo\n"
            "video = VKVideo('not-created.mp4')\n"
            "label = 'not a video source'\n"
        )
        character = source.splitlines()[1].index("not-created")

        preview = preview_at(source, "", ".", 2, character)
        unrelated = preview_at(source, "", ".", 3, 10)

        self.assertIn("not-created.mp4", preview["path"])
        self.assertIn("does not exist", preview["error"])
        self.assertIsNone(unrelated)

    @patch("videokit.video.probe")
    def test_reads_metadata_and_selects_valid_range(self, probe):
        probe.return_value = {
            "streams": [
                {
                    "codec_type": "video",
                    "duration": "12",
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "30000/1001",
                    "codec_name": "h264",
                },
                {"codec_type": "audio"},
            ],
            "format": {},
        }
        with patch.object(Path, "is_file", return_value=True):
            video = Video("movie.mp4")

        clip = video.cut(2, 8)
        self.assertEqual(video.resolution, (1920, 1080))
        self.assertAlmostEqual(video.fps, 30000 / 1001)
        self.assertTrue(video.has_audio)
        self.assertEqual(clip.duration, 6)

    @patch("videokit.video.probe")
    def test_rejects_time_range_outside_video(self, probe):
        probe.return_value = {
            "streams": [
                {
                    "codec_type": "video",
                    "duration": "4",
                    "width": 640,
                    "height": 360,
                    "avg_frame_rate": "24/1",
                    "codec_name": "h264",
                }
            ],
            "format": {},
        }
        with patch.object(Path, "is_file", return_value=True):
            video = Video("movie.mp4")

        with self.assertRaises(ValueError):
            video.cut(0, 5)

    @patch("videokit.video.probe", return_value={"streams": [], "format": {}})
    def test_rejects_file_without_video_stream(self, probe):
        with patch.object(Path, "is_file", return_value=True):
            with self.assertRaises(MediaError):
                Video("audio.mp3")


if __name__ == "__main__":
    unittest.main()
