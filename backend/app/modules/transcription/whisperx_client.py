"""
Speech-to-text client — tries multiple backends in order:

1. Deepgram API (cloud, zero RAM, free tier 12K min/year) — preferred for deployment
2. WhisperX (local, needs GPU/RAM) — for local dev with full ML
3. Mock fallback (fake data) — for CI/testing

Set DEEPGRAM_API_KEY in .env to use Deepgram.
Otherwise falls back to WhisperX if installed, then mock.
"""

import uuid
from pathlib import Path

from app.core.logging import get_logger
from app.core.settings import settings

logger = get_logger(__name__)


def transcribe_and_align(audio_path: str | Path) -> dict:
    """
    Run speech-to-text on a normalized WAV file.
    
    Priority:
      1. Deepgram API (if DEEPGRAM_API_KEY is set)
      2. WhisperX local (if installed)
      3. Mock fallback (dev/CI)

    Returns a dict with:
        raw_text: str — full transcript text
        words: list[dict] — [{word, start, end, confidence}, ...]
        language: str
        model_version: str
    """
    audio_path = str(audio_path)

    # 1. Try Deepgram first (zero RAM, works on free Render)
    deepgram_key = getattr(settings, "deepgram_api_key", "") or ""
    if deepgram_key:
        try:
            result = _deepgram_sync(audio_path, deepgram_key)
            if result:
                return result
            logger.warning("deepgram_returned_none", fallback="whisperx_or_mock")
        except Exception as exc:
            logger.warning("deepgram_failed", error=str(exc), fallback="whisperx_or_mock")

    # 2. Try WhisperX local
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


def _deepgram_sync(audio_path: str, api_key: str) -> dict | None:
    """Synchronous Deepgram API call — works in any context (sync bg tasks)."""
    import httpx

    try:
        with open(audio_path, "rb") as f:
            audio_data = f.read()

        response = httpx.post(
            "https://api.deepgram.com/v1/listen",
            headers={
                "Authorization": f"Token {api_key}",
                "Content-Type": "audio/wav",
            },
            params={"model": "nova-2", "language": "en", "punctuate": "true"},
            content=audio_data,
            timeout=60.0,
        )

        if response.status_code != 200:
            logger.error("deepgram_sync_error", status=response.status_code)
            return None

        data = response.json()
        channels = data.get("results", {}).get("channels", [])
        if not channels:
            return None
        best = channels[0].get("alternatives", [{}])[0]

        words = [
            {
                "word": w.get("word", ""),
                "start": round(w.get("start", 0.0), 3),
                "end": round(w.get("end", 0.0), 3),
                "confidence": round(w.get("confidence", 0.0), 3),
            }
            for w in best.get("words", [])
        ]

        logger.info("deepgram_sync_done", word_count=len(words))
        return {
            "raw_text": best.get("transcript", ""),
            "words": words,
            "language": "en",
            "model_version": "deepgram-nova-2",
        }
    except Exception as exc:
        logger.error("deepgram_sync_failed", error=str(exc))
        return None


def _mock_transcription(audio_path: str) -> dict:
    """
    Mock transcription for dev/CI when WhisperX is not installed.
    Returns a plausible transcript structure using the file duration.
    Varies confidence based on audio path hash so different files get different scores.
    """
    from app.modules.upload.validators import get_audio_duration

    try:
        duration = get_audio_duration(audio_path)
    except Exception:
        duration = 30.0

    # Generate varied mock words spread across the duration
    mock_sentences = [
        "The quick brown fox jumps over the lazy dog while thinking about three things",
        "She sells seashells by the seashore every Thursday morning",
        "Peter picked a peck of pickled peppers from the garden path",
        "The weather is rather warm this afternoon which is very pleasant",
        "I think three hundred thirty three thoughts through the night",
    ]

    # Pick a sentence based on hash of audio path for variety
    path_hash = sum(ord(c) for c in str(audio_path))
    mock_text = mock_sentences[path_hash % len(mock_sentences)]
    mock_words_list = mock_text.split()
    word_duration = duration / max(len(mock_words_list), 1)

    # Vary confidence based on path hash — different files get different quality
    base_confidence = 0.5 + (path_hash % 40) / 100.0  # range 0.50 - 0.89

    words = []
    for i, word in enumerate(mock_words_list):
        start = round(i * word_duration, 3)
        end = round((i + 1) * word_duration - 0.05, 3)
        # Vary confidence per word (some high, some low)
        word_conf = base_confidence + ((i * 7 + path_hash) % 30 - 15) / 100.0
        word_conf = max(0.2, min(0.98, word_conf))
        words.append({
            "word": word,
            "start": start,
            "end": end,
            "confidence": round(word_conf, 3),
        })

    return {
        "raw_text": mock_text,
        "words": words,
        "language": "en",
        "model_version": "mock-dev-fallback",
    }
