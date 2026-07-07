"""
WhisperX client wrapper.

Encapsulates model loading and inference. In production this would run on a
GPU worker; for the assessment it runs in-process on CPU.

If WhisperX is not installed (heavy dependency), falls back to a mock
transcription that returns reasonable placeholder data — allowing the full
pipeline to run end-to-end in lightweight dev/CI environments.

Trade-off documented: CPU inference on Render free tier takes ~15-30s for a
30s clip with the "small" model. GPU-backed inference is the production path.
"""

import uuid
from pathlib import Path

from app.core.logging import get_logger
from app.core.settings import settings

logger = get_logger(__name__)


def transcribe_and_align(audio_path: str | Path) -> dict:
    """
    Run WhisperX transcription + forced alignment on a normalized WAV file.

    Returns a dict with:
        raw_text: str — full transcript text
        words: list[dict] — [{word, start, end, confidence}, ...]
        language: str
        model_version: str

    Falls back to mock output if whisperx is not installed.
    """
    audio_path = str(audio_path)

    try:
        import whisperx
        import torch

        device = settings.whisperx_device
        compute_type = "int8" if device == "cpu" else "float16"
        model_size = settings.whisperx_model_size

        logger.info(
            "whisperx_loading_model",
            model=model_size,
            device=device,
            compute_type=compute_type,
        )

        # 1. Load model and transcribe
        model = whisperx.load_model(
            model_size,
            device=device,
            compute_type=compute_type,
        )
        audio = whisperx.load_audio(audio_path)
        result = model.transcribe(audio, batch_size=4 if device == "cpu" else 16)

        # 2. Forced alignment for word-level timestamps
        align_model, align_metadata = whisperx.load_align_model(
            language_code=result.get("language", "en"),
            device=device,
        )
        aligned = whisperx.align(
            result["segments"],
            align_model,
            align_metadata,
            audio,
            device=device,
            return_char_alignments=False,
        )

        # 3. Extract word-level data
        words = []
        for segment in aligned.get("segments", []):
            for word_info in segment.get("words", []):
                words.append({
                    "word": word_info.get("word", "").strip(),
                    "start": round(word_info.get("start", 0.0), 3),
                    "end": round(word_info.get("end", 0.0), 3),
                    "confidence": round(word_info.get("score", 0.0), 3),
                })

        raw_text = " ".join(seg.get("text", "") for seg in result.get("segments", [])).strip()

        logger.info(
            "whisperx_transcription_done",
            word_count=len(words),
            language=result.get("language", "en"),
        )

        return {
            "raw_text": raw_text,
            "words": words,
            "language": result.get("language", "en"),
            "model_version": f"whisperx-{model_size}-{result.get('language', 'en')}",
        }

    except ImportError:
        logger.warning(
            "whisperx_not_installed",
            fallback="mock_transcription",
            info="Install whisperx + torch for real ASR. Using mock for dev/CI.",
        )
        return _mock_transcription(audio_path)


def _mock_transcription(audio_path: str) -> dict:
    """
    Mock transcription for dev/CI when WhisperX is not installed.
    Returns a plausible transcript structure using the file duration.
    """
    from app.modules.upload.validators import get_audio_duration

    try:
        duration = get_audio_duration(audio_path)
    except Exception:
        duration = 30.0

    # Generate mock words spread across the duration
    mock_text = (
        "The quick brown fox jumps over the lazy dog "
        "while thinking about three things that matter"
    )
    mock_words_list = mock_text.split()
    word_duration = duration / max(len(mock_words_list), 1)

    words = []
    for i, word in enumerate(mock_words_list):
        start = round(i * word_duration, 3)
        end = round((i + 1) * word_duration - 0.05, 3)
        words.append({
            "word": word,
            "start": start,
            "end": end,
            "confidence": round(0.75 + (i % 5) * 0.05, 3),
        })

    return {
        "raw_text": mock_text,
        "words": words,
        "language": "en",
        "model_version": "mock-dev-fallback",
    }
