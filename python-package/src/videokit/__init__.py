"""A beginner-friendly Python interface for basic video editing."""

from .audio import Audio, AudioClip
from .exceptions import FFmpegError, MediaError, VideoKitError
from .render import RenderSettings
from .timeline import Timeline
from .video import Clip, Video

__all__ = [
    "Audio",
    "AudioClip",
    "Clip",
    "FFmpegError",
    "MediaError",
    "RenderSettings",
    "Timeline",
    "Video",
    "VideoKitError",
]
__version__ = "0.1.0"
