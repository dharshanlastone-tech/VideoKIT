"""Exceptions raised by VideoKit."""


class VideoKitError(Exception):
    """Base exception for VideoKit errors."""


class MediaError(VideoKitError):
    """Raised when a media file is missing, invalid, or unsupported."""


class FFmpegError(VideoKitError):
    """Raised when FFmpeg cannot complete a requested operation."""
