"""Video sources, non-destructive clip edits, and FFmpeg export."""

from __future__ import annotations

import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from typing import Any

from ._ffmpeg import probe, run_ffmpeg
from .exceptions import MediaError
from .render import RenderSettings


def _fraction(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        numerator, denominator = value.split("/", 1)
        divisor = float(denominator)
        return float(numerator) / divisor if divisor else None
    except (ValueError, ZeroDivisionError):
        return None


def _seconds(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number of seconds.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite.")
    return result


def _check_destination(path: str | Path, source: Path, overwrite: bool) -> Path:
    destination = Path(path).expanduser().resolve()
    if destination == source:
        raise ValueError("The output file must be different from the source file.")
    if not destination.parent.is_dir():
        raise ValueError(f"Output folder does not exist: '{destination.parent}'.")
    if destination.exists() and not overwrite:
        raise FileExistsError(
            f"Output file already exists: '{destination}'. "
            "Pass overwrite=True to replace it."
        )
    return destination


def _atempo(speed: float) -> list[str]:
    filters: list[str] = []
    remaining = speed
    while remaining > 2:
        filters.append("atempo=2")
        remaining /= 2
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    filters.append(f"atempo={remaining:.9g}")
    return filters


def _encode(
    source: Path,
    destination: Path,
    overwrite: bool,
    *,
    start: float | None = None,
    source_duration: float | None = None,
    filters: tuple[str, ...] = (),
    audio_filters: tuple[str, ...] = (),
    speed: float = 1,
    has_audio: bool = False,
    accurate: bool = True,
    size: tuple[int, int] | None = None,
    fps: float | None = None,
    settings: RenderSettings | None = None,
) -> Path:
    command = [
        shutil.which("ffmpeg") or "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y" if overwrite else "-n",
    ]
    if start is not None:
        command.extend(["-ss", f"{start:.9f}"])
    if source_duration is not None:
        command.extend(["-t", f"{source_duration:.9f}"])
    command.extend(["-i", str(source)])

    should_encode = accurate or speed != 1 or bool(filters or audio_filters) or size
    if not should_encode:
        command.extend(["-map", "0:v:0", "-map", "0:a?", "-c", "copy"])
    else:
        render_settings = settings or RenderSettings()
        video_filters = ["setpts=PTS-STARTPTS"]
        if speed != 1:
            video_filters.append(f"setpts=PTS/{speed:.9g}")
        video_filters.extend(filters)
        if size:
            width, height = size
            video_filters.extend(
                [
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease",
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                    "setsar=1",
                ]
            )
        if fps:
            video_filters.append(f"fps={fps:.9g}")

        video_filters.extend(
            ["pad=ceil(iw/2)*2:ceil(ih/2)*2", "format=yuv420p"]
        )
        graph = f"[0:v:0]{','.join(video_filters)}[v]"
        command.extend(
            [
                "-filter_complex",
                graph,
                "-map",
                "[v]",
                "-c:v",
                "libx264",
                "-preset",
                render_settings.preset,
                "-crf",
                str(render_settings.crf),
            ]
        )
        if has_audio:
            audio_chain = ["asetpts=PTS-STARTPTS"]
            if speed != 1:
                audio_chain.extend(_atempo(speed))
            audio_chain.extend(audio_filters)
            graph += f";[0:a:0]{','.join(audio_chain)},aresample=async=1[a]"
            command[command.index("-filter_complex") + 1] = graph
            command.extend(
                [
                    "-map",
                    "[a]",
                    "-c:a",
                    "aac",
                    "-b:a",
                    render_settings.audio_bitrate,
                ]
            )
        command.extend(["-movflags", "+faststart"])

    command.append(str(destination))
    run_ffmpeg(command, destination)
    return destination


@dataclass(frozen=True)
class Clip:
    """A non-destructive selection and set of edits on a source video."""

    _source: Path
    start: float
    end: float
    _has_audio: bool = False
    _speed: float = 1
    _filters: tuple[str, ...] = ()
    _audio_filters: tuple[str, ...] = ()
    _width: int | None = None
    _height: int | None = None
    _fps: float | None = None

    @property
    def duration(self) -> float:
        """Playback duration in seconds, including any speed change."""
        return (self.end - self.start) / self._speed

    def _edited(
        self,
        *,
        speed: float | None = None,
        filters: tuple[str, ...] = (),
        audio_filters: tuple[str, ...] = (),
        size: tuple[int, int] | None = None,
    ) -> Clip:
        return Clip(
            self._source,
            self.start,
            self.end,
            self._has_audio,
            self._speed if speed is None else speed,
            self._filters + filters,
            self._audio_filters + audio_filters,
            self._width if size is None else size[0],
            self._height if size is None else size[1],
            self._fps,
        )

    def speed(self, factor: float) -> Clip:
        """Set a positive playback-speed multiplier; 2 means twice as fast.

        Audio pitch changes with speed. The source remains unchanged.
        """
        value = _seconds(factor, "factor")
        if value <= 0 or value > 100:
            raise ValueError("factor must be greater than 0 and no more than 100.")
        return self._edited(speed=self._speed * value)

    def rotate(
        self, degrees: float, *, start: float = 0, end: float | None = None
    ) -> Clip:
        """Rotate clockwise for the selected playback-time interval.

        Times are relative to the edited clip, not the original media.
        Exposed pixels are filled with black.
        """
        angle = _seconds(degrees, "degrees")
        first = _seconds(start, "start")
        last = self.duration if end is None else _seconds(end, "end")
        if first < 0 or last <= first or last > self.duration:
            raise ValueError("Rotation times must be within the clip duration.")
        radians = math.radians(angle)
        expression = (
            f"rotate={radians:.12g}:ow=rotw({radians:.12g}):oh=roth({radians:.12g}):c=black"
        )
        if first != 0 or last != self.duration:
            expression += f":enable='between(t,{first:.9g},{last:.9g})'"
        size = None
        if self._width and self._height:
            cosine, sine = abs(math.cos(radians)), abs(math.sin(radians))
            size = (
                math.ceil(self._width * cosine + self._height * sine),
                math.ceil(self._height * cosine + self._width * sine),
            )
        return self._edited(filters=(expression,), size=size)

    def tilt(
        self,
        degrees: float,
        *,
        start: float = 0,
        end: float | None = None,
        from_degrees: float = 0.0,
    ) -> Clip:
        """Smoothly rotate from ``from_degrees`` to ``degrees``.

        The rotation is animated over the selected playback-time interval. The
        output frame grows to fit the largest angle; crop back to the target
        size after this edit to remove the exposed corners.
        """
        target = _seconds(degrees, "degrees")
        origin = _seconds(from_degrees, "from_degrees")
        first = _seconds(start, "start")
        last = self.duration if end is None else _seconds(end, "end")
        if first < 0 or last <= first or last > self.duration:
            raise ValueError("Tilt times must be within the clip duration.")
        start_radians = math.radians(origin)
        end_radians = math.radians(target)
        largest = max(abs(start_radians), abs(end_radians))
        angle = (
            f"if(lt(t,{first:.9g}),{start_radians:.12g},"
            f"if(gt(t,{last:.9g}),{end_radians:.12g},"
            f"{start_radians:.12g}+({end_radians - start_radians:.12g})"
            f"*(t-{first:.9g})/{last - first:.9g}))"
        )
        expression = (
            f"rotate='{angle}':ow=rotw({largest:.12g}):oh=roth({largest:.12g}):c=black"
        )
        size = None
        if self._width and self._height:
            cosine, sine = abs(math.cos(largest)), abs(math.sin(largest))
            size = (
                math.ceil(self._width * cosine + self._height * sine),
                math.ceil(self._height * cosine + self._width * sine),
            )
        return self._edited(filters=(expression,), size=size)

    def resize(self, width: int, height: int) -> Clip:
        """Fit within a new frame size and pad unused space with black."""
        if (
            isinstance(width, bool)
            or isinstance(height, bool)
            or not isinstance(width, int)
            or not isinstance(height, int)
            or width < 2
            or height < 2
            or width % 2
            or height % 2
        ):
            raise ValueError("width and height must be even integers of at least 2.")
        return self._edited(
            filters=(
                f"scale={width}:{height}:force_original_aspect_ratio=decrease",
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                "setsar=1",
            ),
            size=(width, height),
        )

    def _reframe(
        self,
        width: int,
        height: int,
        *,
        mode: Literal["crop", "fit"],
        focus_x: float,
        focus_y: float,
    ) -> Clip:
        if (
            isinstance(width, bool)
            or isinstance(height, bool)
            or not isinstance(width, int)
            or not isinstance(height, int)
            or width < 2
            or height < 2
            or width % 2
            or height % 2
        ):
            raise ValueError("width and height must be even integers of at least 2.")
        if mode not in {"crop", "fit"}:
            raise ValueError("mode must be 'crop' or 'fit'.")
        horizontal = _seconds(focus_x, "focus_x")
        vertical = _seconds(focus_y, "focus_y")
        if not 0 <= horizontal <= 1 or not 0 <= vertical <= 1:
            raise ValueError("focus_x and focus_y must be between 0 and 1.")
        if mode == "crop":
            filters = (
                f"scale={width}:{height}:force_original_aspect_ratio=increase",
                f"crop={width}:{height}:"
                f"x='(iw-ow)*{horizontal:.9g}':"
                f"y='(ih-oh)*{vertical:.9g}'",
                "setsar=1",
            )
        else:
            filters = (
                f"scale={width}:{height}:force_original_aspect_ratio=decrease",
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black",
                "setsar=1",
            )
        return self._edited(filters=filters, size=(width, height))

    def to_vertical(
        self,
        *,
        mode: Literal["crop", "fit"] = "crop",
        width: int = 1080,
        height: int = 1920,
        focus_x: float = 0.5,
        focus_y: float = 0.5,
    ) -> Clip:
        """Reframe as a 9:16 portrait video.

        ``mode="crop"`` fills the frame and trims the sides or top/bottom.
        Adjust ``focus_x`` and ``focus_y`` from 0 to 1 to choose the crop's
        position. ``mode="fit"`` preserves the whole picture with black bars.
        """
        if width * 16 != height * 9:
            raise ValueError("Vertical output dimensions must have a 9:16 ratio.")
        return self._reframe(
            width,
            height,
            mode=mode,
            focus_x=focus_x,
            focus_y=focus_y,
        )

    def to_horizontal(
        self,
        *,
        mode: Literal["crop", "fit"] = "crop",
        width: int = 1920,
        height: int = 1080,
        focus_x: float = 0.5,
        focus_y: float = 0.5,
    ) -> Clip:
        """Reframe as a 16:9 landscape video.

        ``mode="crop"`` fills the frame and trims the sides or top/bottom.
        Adjust ``focus_x`` and ``focus_y`` from 0 to 1 to choose the crop's
        position. ``mode="fit"`` preserves the whole picture with black bars.
        """
        if width * 9 != height * 16:
            raise ValueError("Horizontal output dimensions must have a 16:9 ratio.")
        return self._reframe(
            width,
            height,
            mode=mode,
            focus_x=focus_x,
            focus_y=focus_y,
        )

    def crop(self, width: int, height: int, *, x: int = 0, y: int = 0) -> Clip:
        """Crop a rectangle from the source frame, measured in pixels."""
        values = (width, height, x, y)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise ValueError("width, height, x, and y must be integers.")
        if width < 2 or height < 2 or x < 0 or y < 0:
            raise ValueError("Crop dimensions must be at least 2; x and y cannot be negative.")
        if width % 2 or height % 2:
            raise ValueError("Crop width and height must be even for video export.")
        if self._width and x + width > self._width:
            raise ValueError("Crop extends beyond the source video width.")
        if self._height and y + height > self._height:
            raise ValueError("Crop extends beyond the source video height.")
        return self._edited(
            filters=(f"crop={width}:{height}:{x}:{y}",), size=(width, height)
        )

    def flip(self, *, horizontal: bool = False, vertical: bool = False) -> Clip:
        """Flip horizontally, vertically, or both."""
        if not isinstance(horizontal, bool) or not isinstance(vertical, bool):
            raise ValueError("horizontal and vertical must be booleans.")
        edits = tuple(
            name
            for enabled, name in (
                (horizontal, "hflip"),
                (vertical, "vflip"),
            )
            if enabled
        )
        if not edits:
            raise ValueError("Set horizontal=True and/or vertical=True.")
        return self._edited(filters=edits)

    def brightness(self, amount: float) -> Clip:
        """Adjust brightness from -1 (dark) to 1 (bright); 0 leaves it unchanged."""
        value = _seconds(amount, "amount")
        if not -1 <= value <= 1:
            raise ValueError("amount must be between -1 and 1.")
        return self._edited(filters=(f"eq=brightness={value:.9g}",))

    def contrast(self, amount: float) -> Clip:
        """Set contrast from 0 (flat) to 4 (strong); 1 leaves it unchanged."""
        value = _seconds(amount, "amount")
        if not 0 <= value <= 4:
            raise ValueError("amount must be between 0 and 4.")
        return self._edited(filters=(f"eq=contrast={value:.9g}",))

    def saturation(self, amount: float) -> Clip:
        """Set color saturation from 0 (grayscale) to 3; 1 leaves it unchanged."""
        value = _seconds(amount, "amount")
        if not 0 <= value <= 3:
            raise ValueError("amount must be between 0 and 3.")
        return self._edited(filters=(f"eq=saturation={value:.9g}",))

    def grayscale(self) -> Clip:
        """Convert the picture to grayscale."""
        return self._edited(filters=("hue=s=0",))

    def fade_in(self, duration: float) -> Clip:
        """Fade the picture and audio in from black and silence."""
        seconds = _seconds(duration, "duration")
        if seconds <= 0 or seconds > self.duration:
            raise ValueError("duration must be positive and no longer than the clip.")
        return self._edited(
            filters=(f"fade=t=in:st=0:d={seconds:.9g}",),
            audio_filters=(f"afade=t=in:st=0:d={seconds:.9g}",),
        )

    def fade_out(self, duration: float) -> Clip:
        """Fade the picture and audio out at the end of the clip."""
        seconds = _seconds(duration, "duration")
        if seconds <= 0 or seconds > self.duration:
            raise ValueError("duration must be positive and no longer than the clip.")
        start = self.duration - seconds
        return self._edited(
            filters=(f"fade=t=out:st={start:.9g}:d={seconds:.9g}",),
            audio_filters=(f"afade=t=out:st={start:.9g}:d={seconds:.9g}",),
        )

    def export(
        self,
        output_path: str | Path,
        *,
        overwrite: bool = False,
        accurate: bool = True,
        settings: RenderSettings | None = None,
    ) -> Path:
        """Export the clip as MP4-compatible H.264/AAC.

        Accurate export re-encodes and honors edit timestamps. Set
        ``accurate=False`` to stream-copy an unedited cut quickly; the cut can
        then be limited by codec keyframes. Edited clips always re-encode.
        """
        destination = _check_destination(output_path, self._source, overwrite)
        return _encode(
            self._source,
            destination,
            overwrite,
            start=self.start,
            source_duration=self.end - self.start,
            filters=self._filters,
            audio_filters=self._audio_filters,
            speed=self._speed,
            has_audio=self._has_audio,
            accurate=accurate,
            settings=settings,
        )


class Video:
    """A video file with metadata and non-destructive editing methods."""

    path: Path
    duration: float
    width: int
    height: int
    resolution: tuple[int, int]
    fps: float | None
    codec: str | None
    has_audio: bool

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        if not self.path.is_file():
            raise MediaError(f"Video file does not exist: '{self.path}'.")
        metadata = probe(self.path)
        streams: list[dict[str, Any]] = metadata.get("streams", [])
        stream = next(
            (item for item in streams if item.get("codec_type") == "video"), None
        )
        if stream is None:
            raise MediaError(f"No video stream was found in '{self.path}'.")
        duration_value = stream.get("duration") or metadata.get("format", {}).get(
            "duration"
        )
        try:
            self.duration = float(duration_value)
            self.width = int(stream["width"])
            self.height = int(stream["height"])
        except (KeyError, TypeError, ValueError) as error:
            raise MediaError(f"Required video metadata is unavailable for '{self.path}'.") from error
        if (
            not math.isfinite(self.duration)
            or self.duration <= 0
            or self.width <= 0
            or self.height <= 0
        ):
            raise MediaError(f"Video metadata is invalid for '{self.path}'.")
        self.resolution = (self.width, self.height)
        self.fps = _fraction(stream.get("avg_frame_rate")) or _fraction(
            stream.get("r_frame_rate")
        )
        self.codec = stream.get("codec_name")
        self.has_audio = any(item.get("codec_type") == "audio" for item in streams)

    def cut(self, start: float, end: float) -> Clip:
        """Select video from ``start`` up to (but not including) ``end`` seconds."""
        first = _seconds(start, "start")
        last = _seconds(end, "end")
        if first < 0:
            raise ValueError("start cannot be negative.")
        if last <= first:
            raise ValueError("end must be greater than start.")
        if last > self.duration:
            raise ValueError(
                f"end ({last:g}s) exceeds video duration ({self.duration:g}s)."
            )
        return Clip(
            self.path,
            first,
            last,
            self.has_audio,
            _width=self.width,
            _height=self.height,
            _fps=self.fps,
        )

    def to_vertical(
        self,
        *,
        mode: Literal["crop", "fit"] = "crop",
        width: int = 1080,
        height: int = 1920,
        focus_x: float = 0.5,
        focus_y: float = 0.5,
    ) -> Clip:
        """Reframe the complete video as portrait 9:16; see :meth:`Clip.to_vertical`."""
        return self.cut(0, self.duration).to_vertical(
            mode=mode,
            width=width,
            height=height,
            focus_x=focus_x,
            focus_y=focus_y,
        )

    def to_horizontal(
        self,
        *,
        mode: Literal["crop", "fit"] = "crop",
        width: int = 1920,
        height: int = 1080,
        focus_x: float = 0.5,
        focus_y: float = 0.5,
    ) -> Clip:
        """Reframe the complete video as landscape 16:9; see :meth:`Clip.to_horizontal`."""
        return self.cut(0, self.duration).to_horizontal(
            mode=mode,
            width=width,
            height=height,
            focus_x=focus_x,
            focus_y=focus_y,
        )

    def extract_frame(
        self, timestamp: float, output_path: str | Path, *, overwrite: bool = False
    ) -> Path:
        """Save a still image from the video at ``timestamp`` seconds."""
        time = _seconds(timestamp, "timestamp")
        if time < 0 or time >= self.duration:
            raise ValueError("timestamp must be within the video duration.")
        destination = _check_destination(output_path, self.path, overwrite)
        command = [
            shutil.which("ffmpeg") or "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y" if overwrite else "-n",
            "-ss",
            f"{time:.9f}",
            "-i",
            str(self.path),
            "-frames:v",
            "1",
            str(destination),
        ]
        run_ffmpeg(command, destination)
        return destination

    def thumbnail(
        self,
        output_path: str | Path,
        *,
        timestamp: float | None = None,
        max_width: int = 320,
        max_height: int = 180,
        overwrite: bool = False,
    ) -> Path:
        """Create a small representative image without distorting its aspect ratio.

        If ``timestamp`` is omitted, the frame at the middle of the video is
        used. The output dimensions will not exceed ``max_width`` or
        ``max_height``.
        """
        time = self.duration / 2 if timestamp is None else _seconds(
            timestamp, "timestamp"
        )
        if time < 0 or time >= self.duration:
            raise ValueError("timestamp must be within the video duration.")
        if (
            isinstance(max_width, bool)
            or isinstance(max_height, bool)
            or not isinstance(max_width, int)
            or not isinstance(max_height, int)
            or max_width < 1
            or max_height < 1
        ):
            raise ValueError("max_width and max_height must be positive integers.")
        destination = _check_destination(output_path, self.path, overwrite)
        command = [
            shutil.which("ffmpeg") or "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y" if overwrite else "-n",
            "-ss",
            f"{time:.9f}",
            "-i",
            str(self.path),
            "-frames:v",
            "1",
            "-vf",
            f"scale={max_width}:{max_height}:force_original_aspect_ratio=decrease",
            str(destination),
        ]
        run_ffmpeg(command, destination)
        return destination

    def export(self, output_path: str | Path, *, overwrite: bool = False) -> Path:
        """Copy the whole source without re-encoding."""
        destination = _check_destination(output_path, self.path, overwrite)
        command = [
            shutil.which("ffmpeg") or "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y" if overwrite else "-n",
            "-i",
            str(self.path),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c",
            "copy",
            str(destination),
        ]
        run_ffmpeg(command, destination)
        return destination
