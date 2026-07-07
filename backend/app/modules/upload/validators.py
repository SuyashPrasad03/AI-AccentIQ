"""
Upload validation — MIME type, file size, and audio duration checks.

These run server-side and are authoritative. Client-side checks are UX niceties only.
"""

import json
import subprocess
import tempfile
from pathlib import Path

from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.core.settings import settings

logger = get_logger(__name__)

# Audio MIME types we accept (content-type sniffed from bytes, not file extension)
_ALLOWED_MIMES = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/x-m4a",
    "audio/ogg",
    "audio/flac",
    "audio/webm",
    "audio/aac",
    "video/webm",  # browser MediaRecorder often produces video/webm with audio only
}


def validate_mime_type(content_type: str | None, file_bytes: bytes) -> str:
    """
    Validate the MIME type via python-magic (libmagic) byte sniffing.
    Never trust the Content-Type header or file extension alone.
    Returns the detected MIME string.

    Raises ValidationError if not an audio type.
    """
    try:
        import magic
        detected = magic.from_buffer(file_bytes[:8192], mime=True)
    except ImportError:
        # Fallback if python-magic isn't available (e.g. test env without libmagic)
        detected = content_type or "application/octet-stream"

    logger.info("mime_detected", detected=detected, header=content_type)

    if detected not in _ALLOWED_MIMES:
        raise ValidationError(
            message=f"Unsupported file type: {detected}. Please upload an audio file.",
            details={"detected_mime": detected, "allowed": list(_ALLOWED_MIMES)},
        )
    return detected


def validate_file_size(size: int) -> None:
    """Raise ValidationError if file exceeds the max upload size."""
    if size > settings.audio_max_size_bytes:
        max_mb = settings.audio_max_size_bytes / (1024 * 1024)
        raise ValidationError(
            message=f"File is too large. Maximum allowed size is {max_mb:.0f} MB.",
            details={"size_bytes": size, "max_bytes": settings.audio_max_size_bytes},
        )


def get_audio_duration(file_path: str | Path) -> float:
    """
    Use ffprobe to get the exact duration in seconds.
    This is the authoritative server-side check.

    Raises ValidationError if ffprobe fails or returns no duration.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise ValidationError(
                message="Could not read audio file. It may be corrupted.",
                details={"ffprobe_stderr": result.stderr[:500]},
            )

        info = json.loads(result.stdout)
        duration = float(info.get("format", {}).get("duration", 0))

        if duration <= 0:
            raise ValidationError(
                message="Could not determine audio duration. File may be corrupted.",
            )

        return duration

    except subprocess.TimeoutExpired:
        raise ValidationError(message="Audio analysis timed out. File may be too large or corrupted.")
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValidationError(
            message="Failed to parse audio metadata.",
            details={"error": str(exc)},
        )


def validate_duration(duration: float) -> None:
    """
    Check the duration is within the allowed range [min, max].
    Raises ValidationError with a clear message if outside bounds.
    """
    min_dur = settings.audio_min_duration_seconds
    max_dur = settings.audio_max_duration_seconds

    if duration < min_dur:
        raise ValidationError(
            message=f"Recording is too short ({duration:.1f}s). Minimum is {min_dur:.0f} seconds.",
            details={"duration": duration, "min": min_dur, "max": max_dur},
        )

    if duration > max_dur:
        raise ValidationError(
            message=f"Recording is too long ({duration:.1f}s). Maximum is {max_dur:.0f} seconds.",
            details={"duration": duration, "min": min_dur, "max": max_dur},
        )
