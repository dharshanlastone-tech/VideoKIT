"""Small, safe wrappers around the FFmpeg command-line tools."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .exceptions import FFmpegError, MediaError


def _tool_path(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise FFmpegError(
            f"{name} was not found. Install FFmpeg and make sure its bin folder "
            "is on your PATH."
        )
    return executable


def probe(path: Path) -> dict[str, Any]:
    command = [
        _tool_path("ffprobe"),
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=False
        )
    except OSError as error:
        raise FFmpegError(f"Could not start ffprobe: {error}") from error
    if result.returncode:
        details = result.stderr.strip() or "ffprobe could not read this file."
        raise MediaError(f"Could not read video '{path}': {details}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise FFmpegError("ffprobe returned invalid metadata.") from error


def run_ffmpeg(command: list[str], output_path: Path) -> None:
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=False
        )
    except OSError as error:
        raise FFmpegError(f"Could not start FFmpeg: {error}") from error
    if result.returncode:
        details = result.stderr.strip() or "FFmpeg returned an unknown error."
        raise FFmpegError(
            f"Could not export '{output_path}': {details}"
        )
