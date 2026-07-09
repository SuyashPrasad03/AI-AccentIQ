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
    For browser-recorded blobs (application/octet-stream), we allow them
    through and let ffprobe validate the actual audio content downstream.
    """
    try:
        import magic
        detected = magic.from_buffer(file_bytes[:8192], mime=True)
    except ImportError:
        # Fallback if python-magic isn't available
        detected = content_type or "application/octet-stream"

    logger.info("mime_detected", detected=detected, header=content_type)

    # Strip codec parameters (e.g. "audio/webm;codecs=opus" → "audio/webm")
    base_mime = detected.split(";")[0].strip().lower()

    # Allow application/octet-stream through — browser MediaRecorder often
    # produces blobs with this type. ffprobe will reject truly invalid files.
    if base_mime == "application/octet-stream":
        return detected

    if base_mime not in _ALLOWED_MIMES:
        raise ValidationError(
            message=f"Unsupported file type: {detected}. Please upload an audio file (MP3, WAV, M4A, WebM).",
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

    Tries format duration first, falls back to stream duration.
    Raises ValidationError if ffprobe fails or returns no duration.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise ValidationError(
                message="We couldn't read that file — try re-recording or uploading a different format (MP3, WAV, M4A).",
                details={"ffprobe_stderr": result.stderr[:500]},
            )

        info = json.loads(result.stdout)

        # Try format duration first
        duration = float(info.get("format", {}).get("duration", 0))

        # Fallback: try stream duration (WebM often has it here instead)
        if duration <= 0:
            for stream in info.get("streams", []):
                stream_dur = float(stream.get("duration", 0))
                if stream_dur > 0:
                    duration = stream_dur
                    break

        # Last fallback: estimate from format bit_rate and size
        if duration <= 0:
            fmt = info.get("format", {})
            size = float(fmt.get("size", 0))
            bit_rate = float(fmt.get("bit_rate", 0))
            if size > 0 and bit_rate > 0:
                duration = size * 8 / bit_rate

        if duration <= 0:
            raise ValidationError(
                message="We couldn't determine the length of your recording. Try recording again or upload an MP3/WAV file.",
            )

        return duration

    except subprocess.TimeoutExpired:
        raise ValidationError(message="Audio analysis timed out. File may be too large or corrupted.")
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValidationError(
            message="We couldn't read that file. Try a different format (MP3, WAV, M4A).",
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
