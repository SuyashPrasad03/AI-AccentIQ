"""
FFmpeg audio preprocessing pipeline.

Normalizes any input audio to the format WhisperX expects:
  - 16kHz sample rate
  - Mono channel
  - WAV (PCM s16le)

This runs synchronously via subprocess — fast enough for short clips (15-45s).
For production scale, move to a background worker (Celery/RQ).
"""

import subprocess
import tempfile
from pathlib import Path

from app.core.exceptions import ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Output format: 16kHz mono WAV (PCM signed 16-bit little-endian)
_OUTPUT_SAMPLE_RATE = "16000"
_OUTPUT_CHANNELS = "1"
_OUTPUT_FORMAT = "wav"
_OUTPUT_CODEC = "pcm_s16le"


def normalize_audio(input_path: str | Path, output_path: str | Path | None = None) -> Path:
    """
    Normalize audio file to 16kHz mono WAV using FFmpeg.

    Args:
        input_path: Path to the raw uploaded audio file.
        output_path: Where to write the normalized WAV.
                     If None, writes to a temp file and returns its path.

    Returns:
        Path to the normalized WAV file.

    Raises:
        ValidationError if FFmpeg fails (corrupted/unsupported input).
    """
    input_path = Path(input_path)

    if output_path is None:
        output_path = Path(tempfile.mktemp(suffix=".wav"))
    else:
        output_path = Path(output_path)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",                    # overwrite without asking
        "-i", str(input_path),   # input
        "-ar", _OUTPUT_SAMPLE_RATE,   # 16kHz
        "-ac", _OUTPUT_CHANNELS,      # mono
        "-c:a", _OUTPUT_CODEC,        # PCM s16le
        "-f", _OUTPUT_FORMAT,         # WAV container
        str(output_path),
    ]

    logger.info("ffmpeg_normalize_start", input=str(input_path), output=str(output_path))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        raise ValidationError(
            message="Audio normalization timed out. The file may be too large or corrupted."
        )

    if result.returncode != 0:
        logger.error("ffmpeg_failed", returncode=result.returncode, stderr=result.stderr[:500])
        raise ValidationError(
            message="Audio preprocessing failed. The file may be corrupted or in an unsupported format.",
            details={"ffmpeg_error": result.stderr[:300]},
        )

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ValidationError(
            message="Audio normalization produced an empty file. Input may be silent or corrupted."
        )

    logger.info(
        "ffmpeg_normalize_done",
        output=str(output_path),
        output_size=output_path.stat().st_size,
    )
    return output_path
