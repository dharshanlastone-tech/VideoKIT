"""Audio metadata and non-destructive audio clips."""

from __future__ import annotations

import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._ffmpeg import probe, run_ffmpeg
from .exceptions import MediaError
from .video import _atempo, _check_destination, _seconds


@dataclass(frozen=True)
class AudioClip:
    """A selected audio range with optional volume, speed, and fades."""

    _source: Path
    start: float
    end: float
    _speed: float = 1
    _volume: float = 1
    _filters: tuple[str, ...] = ()

    @property
    def duration(self) -> float:
        """Playback duration in seconds."""
        return (self.end - self.start) / self._speed

    def speed(self, factor: float) -> AudioClip:
        """Change playback speed by a positive multiplier without pitch correction."""
        value = _seconds(factor, "factor")
        if value <= 0 or value > 100:
            raise ValueError("factor must be greater than 0 and no more than 100.")
        return AudioClip(
            self._source, self.start, self.end,
            self._speed * value, self._volume, self._filters,
        )

    def volume(self, level: float) -> AudioClip:
        """Set volume from 0 (silent) to 4 (four times as loud)."""
        value = _seconds(level, "level")
        if not 0 <= value <= 4:
            raise ValueError("level must be between 0 and 4.")
        return AudioClip(
            self._source, self.start, self.end, self._speed, value, self._filters
        )

    def fade_in(self, duration: float) -> AudioClip:
        """Fade audio in from silence."""
        seconds = _seconds(duration, "duration")
        if seconds <= 0 or seconds > self.duration:
            raise ValueError("duration must be positive and no longer than the clip.")
        return AudioClip(
            self._source, self.start, self.end, self._speed, self._volume,
            self._filters + (f"afade=t=in:st=0:d={seconds:.9g}",),
        )

    def fade_out(self, duration: float) -> AudioClip:
        """Fade audio out at the end of the clip."""
        seconds = _seconds(duration, "duration")
        if seconds <= 0 or seconds > self.duration:
            raise ValueError("duration must be positive and no longer than the clip.")
        start = self.duration - seconds
        return AudioClip(
            self._source, self.start, self.end, self._speed, self._volume,
            self._filters + (f"afade=t=out:st={start:.9g}:d={seconds:.9g}",),
        )

    def export(
        self, output_path: str | Path, *, overwrite: bool = False
    ) -> Path:
        """Export this selection as AAC, MP3, or PCM audio based on its extension."""
        destination = _check_destination(output_path, self._source, overwrite)
        command = [
            shutil.which("ffmpeg") or "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y" if overwrite else "-n",
            "-ss",
            f"{self.start:.9f}",
            "-t",
            f"{self.end - self.start:.9f}",
            "-i",
            str(self._source),
            "-vn",
        ]
        filters = [*_atempo(self._speed), f"volume={self._volume:.9g}"]
        filters.extend(self._filters)
        command.extend(["-af", ",".join(filters)])
        suffix = destination.suffix.lower()
        if suffix == ".wav":
            command.extend(["-c:a", "pcm_s16le"])
        elif suffix == ".mp3":
            command.extend(["-c:a", "libmp3lame"])
        else:
            command.extend(["-c:a", "aac"])
        command.append(str(destination))
        run_ffmpeg(command, destination)
        return destination


class Audio:
    """An audio file with basic metadata and time-range selection."""

    path: Path
    duration: float
    codec: str | None
    sample_rate: int | None
    channels: int | None

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        if not self.path.is_file():
            raise MediaError(f"Audio file does not exist: '{self.path}'.")
        metadata = probe(self.path)
        streams: list[dict[str, Any]] = metadata.get("streams", [])
        stream = next(
            (item for item in streams if item.get("codec_type") == "audio"), None
        )
        if stream is None:
            raise MediaError(f"No audio stream was found in '{self.path}'.")
        duration_value = stream.get("duration") or metadata.get("format", {}).get(
            "duration"
        )
        try:
            self.duration = float(duration_value)
        except (TypeError, ValueError) as error:
            raise MediaError(f"Audio duration is unavailable for '{self.path}'.") from error
        if not math.isfinite(self.duration) or self.duration <= 0:
            raise MediaError(f"Audio duration is invalid for '{self.path}'.")
        self.codec = stream.get("codec_name")
        try:
            self.sample_rate = (
                int(stream["sample_rate"]) if stream.get("sample_rate") else None
            )
            self.channels = int(stream["channels"]) if stream.get("channels") else None
        except (TypeError, ValueError) as error:
            raise MediaError(f"Audio metadata is invalid for '{self.path}'.") from error

    def cut(self, start: float, end: float) -> AudioClip:
        """Select audio from ``start`` up to (but not including) ``end`` seconds."""
        first = _seconds(start, "start")
        last = _seconds(end, "end")
        if first < 0:
            raise ValueError("start cannot be negative.")
        if last <= first:
            raise ValueError("end must be greater than start.")
        if last > self.duration:
            raise ValueError(
                f"end ({last:g}s) exceeds audio duration ({self.duration:g}s)."
            )
        return AudioClip(self.path, first, last)
