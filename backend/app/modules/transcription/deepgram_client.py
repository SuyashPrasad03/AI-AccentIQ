"""
Deepgram API client — cloud-based ASR alternative to WhisperX.

Advantages over WhisperX for deployment:
  - Zero RAM/GPU requirements (API call)
  - Word-level timestamps + confidence scores
  - Works on free Render tier (512MB)
  - Free tier: 12,000 minutes/year

Set DEEPGRAM_API_KEY in .env to use. If not set, falls back to WhisperX/mock.
"""

import httpx

from app.core.logging import get_logger
from app.core.settings import settings

logger = get_logger(__name__)

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


async def transcribe_with_deepgram(audio_path: str) -> dict | None:
    """
    Send audio to Deepgram for transcription with word-level timestamps.
    
    Returns same format as whisperx_client:
        {raw_text, words: [{word, start, end, confidence}], language, model_version}
    
    Returns None if Deepgram is not configured or fails.
    """
    api_key = getattr(settings, "deepgram_api_key", "") or ""
    if not api_key:
        return None

    try:
        with open(audio_path, "rb") as f:
            audio_data = f.read()

        headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "audio/wav",
        }

        params = {
            "model": "nova-2",
            "language": "en",
            "punctuate": "true",
            "diarize": "false",
            "smart_format": "true",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                DEEPGRAM_URL,
                headers=headers,
                params=params,
                content=audio_data,
            )

        if response.status_code != 200:
            logger.error("deepgram_error", status=response.status_code, body=response.text[:200])
            return None

        data = response.json()
        
        # Extract words from Deepgram response
        channels = data.get("results", {}).get("channels", [])
        if not channels:
            return None

        alternatives = channels[0].get("alternatives", [])
        if not alternatives:
            return None

        best = alternatives[0]
        raw_text = best.get("transcript", "")
        
        words = []
        for w in best.get("words", []):
            words.append({
                "word": w.get("word", ""),
                "start": round(w.get("start", 0.0), 3),
                "end": round(w.get("end", 0.0), 3),
                "confidence": round(w.get("confidence", 0.0), 3),
            })

        logger.info(
            "deepgram_transcription_done",
            word_count=len(words),
            text_preview=raw_text[:50],
        )

        return {
            "raw_text": raw_text,
            "words": words,
            "language": "en",
            "model_version": "deepgram-nova-2",
        }

    except Exception as exc:
        logger.error("deepgram_failed", error=str(exc))
        return None
