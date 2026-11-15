"""Sequential video composition and positioned audio tracks."""

from __future__ import annotations

import math
import shutil
from pathlib import Path

from ._ffmpeg import run_ffmpeg
from .audio import AudioClip
from .exceptions import VideoKitError
from .render import Quality, RenderSettings
from .video import Clip, _atempo, _check_destination, _seconds


class Timeline:
    """Arrange video clips in order and mix audio clips at chosen positions.

    ``add(clip, crossfade=1)`` crossfades from the previous clip over one
    second. The first clip cannot have a crossfade. Clips otherwise meet with
    a direct cut.
    """

    def __init__(self) -> None:
        self._clips: list[tuple[Clip, float]] = []
        self._audio: list[tuple[AudioClip, float]] = []

    @property
    def duration(self) -> float:
        """Total timeline duration in seconds, including any crossfades."""
        if not self._clips:
            return 0
        total = sum(clip.duration for clip, _ in self._clips)
        return total - sum(transition for _, transition in self._clips)

    def add(self, clip: Clip, *, crossfade: float = 0) -> Timeline:
        """Add a video clip to the end, optionally crossfading from its predecessor."""
        if not isinstance(clip, Clip):
            raise TypeError("add() expects a Clip returned by Video.cut().")
        seconds = _seconds(crossfade, "crossfade")
        if seconds < 0:
            raise ValueError("crossfade cannot be negative.")
        if not self._clips and seconds:
            raise ValueError("The first clip cannot have a crossfade.")
        if seconds and (
            seconds >= clip.duration or seconds >= self._clips[-1][0].duration
        ):
            raise ValueError("crossfade must be shorter than both neighboring clips.")
        self._clips.append((clip, seconds))
        return self

    def add_audio(self, clip: AudioClip, *, at: float = 0) -> Timeline:
        """Mix an audio clip at a nonnegative timeline position, in seconds."""
        if not isinstance(clip, AudioClip):
            raise TypeError("add_audio() expects a clip returned by Audio.cut().")
        position = _seconds(at, "at")
        if position < 0:
            raise ValueError("at cannot be negative.")
        if position >= self.duration:
            raise ValueError("Audio must start before the end of the video timeline.")
        self._audio.append((clip, position))
        return self

    def export(
        self,
        output_path: str | Path,
        *,
        overwrite: bool = False,
        width: int | None = None,
        height: int | None = None,
        fps: float | None = None,
        settings: RenderSettings | None = None,
    ) -> Path:
        """Render the timeline to an H.264/AAC MP4-compatible video.

        Clips are normalized to the first clip's dimensions and frame rate by
        default. Audio from video clips is retained and positioned audio tracks
        are mixed with it. Missing clip audio becomes silence during assembly.
        """
        if not self._clips:
            raise VideoKitError("Add at least one video clip before exporting.")
        first = self._clips[0][0]
        out_width = first._width if width is None else width
        out_height = first._height if height is None else height
        out_fps = (first._fps or 30.0) if fps is None else _seconds(fps, "fps")
        if (
            isinstance(out_width, bool)
            or isinstance(out_height, bool)
            or not isinstance(out_width, int)
            or not isinstance(out_height, int)
            or out_width < 2
            or out_height < 2
            or out_width % 2
            or out_height % 2
        ):
            raise ValueError("width and height must be even integers of at least 2.")
        if out_fps is None or not math.isfinite(out_fps) or out_fps <= 0:
            raise ValueError("fps must be a positive number.")
        render_settings = settings or RenderSettings()

        destination = _check_destination(
            output_path, first._source, overwrite
        )
        clips = [item[0] for item in self._clips]
        audio_tracks = [item[0] for item in self._audio]
        all_sources = {clip._source for clip in clips}
        all_sources.update(clip._source for clip in audio_tracks)
        if destination in all_sources:
            raise ValueError("The output file must be different from every source file.")
        command = [
            shutil.which("ffmpeg") or "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y" if overwrite else "-n",
        ]
        for clip in clips:
            command.extend(["-i", str(clip._source)])
        for audio in audio_tracks:
            command.extend(["-i", str(audio._source)])

        graph: list[str] = []
        video_labels: list[str] = []
        audio_labels: list[str] = []
        for index, (clip, _) in enumerate(self._clips):
            video_chain = [
                f"trim=start={clip.start:.9g}:end={clip.end:.9g}",
                "setpts=PTS-STARTPTS",
            ]
            if clip._speed != 1:
                video_chain.append(f"setpts=PTS/{clip._speed:.9g}")
            video_chain.extend(clip._filters)
            video_chain.extend(
                [
                    f"scale={out_width}:{out_height}:force_original_aspect_ratio=decrease",
                    f"pad={out_width}:{out_height}:(ow-iw)/2:(oh-ih)/2",
                    "setsar=1",
                    f"fps={out_fps:.9g}",
                    "format=yuv420p",
                    "settb=AVTB",
                    "setpts=PTS-STARTPTS",
                ]
            )
            video_label = f"v{index}"
            graph.append(f"[{index}:v:0]{','.join(video_chain)}[{video_label}]")
            video_labels.append(video_label)

            audio_label = f"a{index}"
            if clip._has_audio:
                audio_chain = [
                    f"atrim=start={clip.start:.9g}:end={clip.end:.9g}",
                    "asetpts=PTS-STARTPTS",
                ]
                if clip._speed != 1:
                    audio_chain.extend(_atempo(clip._speed))
                audio_chain.extend(clip._audio_filters)
                graph.append(
                    f"[{index}:a:0]{','.join(audio_chain)},"
                    f"apad=whole_dur={clip.duration:.9g},"
                    f"atrim=duration={clip.duration:.9g},"
                    f"aresample=48000,aformat=channel_layouts=stereo[{audio_label}]"
                )
            else:
                graph.append(
                    "anullsrc=r=48000:cl=stereo,"
                    f"atrim=duration={clip.duration:.9g}[{audio_label}]"
                )
            audio_labels.append(audio_label)

        current_video = video_labels[0]
        current_audio = audio_labels[0]
        elapsed = clips[0].duration
        for index in range(1, len(clips)):
            transition = self._clips[index][1]
            next_video = video_labels[index]
            next_audio = audio_labels[index]
            out_video = f"joined_v{index}"
            out_audio = f"joined_a{index}"
            if transition:
                offset = elapsed - transition
                graph.append(
                    f"[{current_video}][{next_video}]"
                    f"xfade=transition=fade:duration={transition:.9g}:"
                    f"offset={offset:.9g}[{out_video}]"
                )
                graph.append(
                    f"[{current_audio}][{next_audio}]"
                    f"acrossfade=d={transition:.9g}:c1=tri:c2=tri[{out_audio}]"
                )
                elapsed += clips[index].duration - transition
            else:
                graph.append(
                    f"[{current_video}][{current_audio}]"
                    f"[{next_video}][{next_audio}]concat=n=2:v=1:a=1"
                    f"[{out_video}][{out_audio}]"
                )
                elapsed += clips[index].duration
            current_video, current_audio = out_video, out_audio

        final_audio = current_audio
        if self._audio:
            mixed_labels = [current_audio]
            for index, (clip, position) in enumerate(self._audio):
                input_index = len(clips) + index
                label = f"track{index}"
                chain = [
                    f"atrim=start={clip.start:.9g}:end={clip.end:.9g}",
                    "asetpts=PTS-STARTPTS",
                ]
                if clip._speed != 1:
                    chain.extend(_atempo(clip._speed))
                chain.extend(
                    [
                        f"volume={clip._volume:.9g}",
                        *clip._filters,
                        f"adelay={round(position * 1000)}:all=1",
                        "aresample=48000",
                        "aformat=channel_layouts=stereo",
                    ]
                )
                graph.append(f"[{input_index}:a:0]{','.join(chain)}[{label}]")
                mixed_labels.append(label)
            final_audio = "mixed_audio"
            inputs = "".join(f"[{label}]" for label in mixed_labels)
            graph.append(
                f"{inputs}amix=inputs={len(mixed_labels)}:duration=first:"
                f"normalize=0,atrim=duration={self.duration:.9g}"
                f"[{final_audio}]"
            )

        command.extend(
            [
                "-filter_complex",
                ";".join(graph),
                "-map",
                f"[{current_video}]",
                "-map",
                f"[{final_audio}]",
                "-c:v",
                "libx264",
                "-preset",
                render_settings.preset,
                "-crf",
                str(render_settings.crf),
                "-c:a",
                "aac",
                "-b:a",
                render_settings.audio_bitrate,
                "-movflags",
                "+faststart",
                str(destination),
            ]
        )
        run_ffmpeg(command, destination)
        return destination

    def render(
        self,
        output_path: str | Path,
        *,
        quality: Quality = "balanced",
        overwrite: bool = False,
        width: int | None = None,
        height: int | None = None,
        fps: float | None = None,
    ) -> Path:
        """Render the finished timeline using a simple named quality preset.

        ``draft`` renders faster, ``balanced`` is the default, and ``high``
        prioritizes image quality at the cost of time and file size.
        """
        settings = RenderSettings(quality=quality)
        return self.export(
            output_path,
            overwrite=overwrite,
            width=width,
            height=height,
            fps=fps,
            settings=settings,
        )
