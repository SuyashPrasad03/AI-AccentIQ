"""
Phase 30 — Rolling-Buffer Incremental Streaming Scorer

Processes audio in chunks as it arrives via WebSocket, running incremental
GOP scoring per detected word boundary. Emits score events in real-time
rather than waiting for the full recording.

Design:
  - Maintains a rolling audio buffer (grows as chunks arrive)
  - Uses WhisperX/Deepgram for incremental transcription on the buffer
  - Runs GOP scoring on each newly-detected word
  - Emits score events via callback (WebSocket sends these to client)
  - Stores the full audio buffer for batch fallback if connection drops

Latency target: word-level feedback within ~1-2 seconds of word spoken.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Awaitable

import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)

# Minimum buffer size before attempting transcription (1.5 seconds)
MIN_BUFFER_SECONDS = 1.5
# How often to run incremental transcription (every N seconds of new audio)
TRANSCRIPTION_INTERVAL_SECONDS = 1.0
# Sample rate expected from client
SAMPLE_RATE = 16000


@dataclass
class WordScoreEvent:
    """A single word score event emitted during streaming."""
    word: str
    index: int
    score: float  # 0-100
    issue: str  # correct|mispronounced|unclear|mistimed
    timestamp: float  # when this word ended (seconds from start)
    latency_ms: float  # time from word spoken to score emitted


@dataclass
class StreamingSession:
    """State for a single streaming scoring session."""
    session_id: str
    audio_buffer: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float32))
    words_scored: int = 0
    last_transcription_length: float = 0.0  # seconds of audio last transcribed
    start_time: float = field(default_factory=time.time)
    is_active: bool = True
    all_word_events: list[WordScoreEvent] = field(default_factory=list)

    @property
    def buffer_duration(self) -> float:
        return len(self.audio_buffer) / SAMPLE_RATE

    def append_audio(self, chunk: np.ndarray):
        self.audio_buffer = np.concatenate([self.audio_buffer, chunk])

    def should_transcribe(self) -> bool:
        """Check if enough new audio has arrived to run transcription."""
        new_audio = self.buffer_duration - self.last_transcription_length
        return (
            self.buffer_duration >= MIN_BUFFER_SECONDS
            and new_audio >= TRANSCRIPTION_INTERVAL_SECONDS
        )


async def process_audio_chunk(
    session: StreamingSession,
    chunk: bytes,
    on_word_score: Callable[[WordScoreEvent], Awaitable[None]],
) -> None:
    """
    Process an incoming audio chunk and emit word scores for any new words detected.

    Args:
        session: The streaming session state
        chunk: Raw audio bytes (16-bit PCM, 16kHz, mono)
        on_word_score: Async callback to emit score events (WebSocket send)
    """
    # Convert bytes to float32 array
    audio_chunk = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
    session.append_audio(audio_chunk)

    # Check if we should run incremental transcription
    if not session.should_transcribe():
        return

    # Run transcription + scoring on the full buffer so far
    try:
        new_events = await _run_incremental_scoring(session)
        session.last_transcription_length = session.buffer_duration

        # Emit only NEW word scores (not previously scored words)
        for event in new_events:
            session.all_word_events.append(event)
            await on_word_score(event)

    except Exception as exc:
        logger.error("streaming_scoring_error", error=str(exc), session=session.session_id)


async def _run_incremental_scoring(session: StreamingSession) -> list[WordScoreEvent]:
    """
    Run transcription + GOP scoring on the current buffer.
    Returns only NEW word score events (words not previously scored).
    """
    import tempfile
    import scipy.io.wavfile as wavfile

    from app.modules.scoring.phoneme_recognizer import get_frame_log_probs
    from app.modules.scoring.gop_engine import compute_gop_scores
    from app.modules.scoring.score_normalizer import normalize_word_scores
    from app.modules.scoring.phoneme_compare import get_reference_phonemes
    from app.modules.transcription.whisperx_client import transcribe_and_align

    # Write buffer to a temp WAV file for WhisperX (it needs a file path)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name
        audio_int16 = (session.audio_buffer * 32768).astype(np.int16)
        wavfile.write(temp_path, SAMPLE_RATE, audio_int16)

    try:
        # Transcribe the full buffer
        transcript = transcribe_and_align(temp_path)
        words = transcript["words"]

        if not words or len(words) <= session.words_scored:
            return []

        # Get new words only
        new_words = words[session.words_scored:]

        # Run GOP on new words
        recognition = get_frame_log_probs(session.audio_buffer, SAMPLE_RATE)
        ref_phonemes = [get_reference_phonemes(w["word"]) for w in new_words]
        gop_results = compute_gop_scores(recognition, new_words, ref_phonemes)
        normalized = normalize_word_scores(gop_results)

        # Build score events
        events = []
        current_time = time.time()

        for i, ws in enumerate(normalized):
            word_info = new_words[i]
            word_end_time = word_info.get("end", 0.0)
            # Latency = time since the word was spoken to now
            word_spoken_at = session.start_time + word_end_time
            latency_ms = (current_time - word_spoken_at) * 1000

            events.append(WordScoreEvent(
                word=ws["word"],
                index=session.words_scored + i,
                score=ws["word_score"],
                issue=ws["detected_issue"],
                timestamp=word_end_time,
                latency_ms=round(max(0, latency_ms), 0),
            ))

        session.words_scored = len(words)
        return events

    finally:
        # Clean up temp file
        Path(temp_path).unlink(missing_ok=True)


def save_buffer_for_fallback(session: StreamingSession) -> str | None:
    """
    Save the accumulated audio buffer as a WAV file for batch processing fallback.
    Called when WebSocket connection drops mid-stream.

    Returns the saved file path, or None if buffer is too short.
    """
    import uuid
    import scipy.io.wavfile as wavfile

    if session.buffer_duration < 1.0:
        return None  # Too short to be useful

    from app.core.settings import settings
    storage_root = Path(settings.storage_local_root)
    storage_root.mkdir(parents=True, exist_ok=True)

    filename = f"stream_{uuid.uuid4().hex}.wav"
    filepath = storage_root / "recordings" / filename

    filepath.parent.mkdir(parents=True, exist_ok=True)
    audio_int16 = (session.audio_buffer * 32768).astype(np.int16)
    wavfile.write(str(filepath), SAMPLE_RATE, audio_int16)

    logger.info(
        "streaming_buffer_saved",
        session=session.session_id,
        duration=round(session.buffer_duration, 1),
        path=str(filepath),
    )

    return str(filepath.relative_to(storage_root))
