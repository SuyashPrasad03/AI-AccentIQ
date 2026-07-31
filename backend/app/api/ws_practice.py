"""
Phase 30 — WebSocket Streaming Practice Endpoint

Streams microphone audio from the client, processes it incrementally,
and sends back word-level scores in real-time.

Protocol:
  Client → Server: binary audio frames (16-bit PCM, 16kHz, mono)
  Server → Client: JSON score events:
    {"type": "word_score", "word": "hello", "index": 0, "score": 85.2, "issue": "correct", "latency_ms": 1200}
    {"type": "status", "message": "listening"}
    {"type": "session_end", "total_words": 10, "overall_score": 72.5}
    {"type": "error", "message": "..."}

Connection lifecycle:
  1. Client connects to ws://host/ws/practice
  2. Server sends {"type": "status", "message": "ready"}
  3. Client streams binary audio chunks
  4. Server sends word_score events as words are detected
  5. Client sends text message "END" when done recording
  6. Server sends session_end summary
  7. On unexpected disconnect: buffer is saved for batch fallback
"""

import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.modules.scoring.streaming_scorer import (
    StreamingSession,
    WordScoreEvent,
    process_audio_chunk,
    save_buffer_for_fallback,
)

logger = get_logger(__name__)

router = APIRouter()


@router.websocket("/ws/practice")
async def websocket_practice(websocket: WebSocket):
    """
    WebSocket endpoint for real-time streaming pronunciation practice.
    Receives audio chunks, returns word-level scores incrementally.
    """
    await websocket.accept()

    session_id = str(uuid.uuid4())[:8]
    session = StreamingSession(session_id=session_id)

    logger.info("ws_practice_connected", session=session_id)

    # Send ready status
    await websocket.send_json({
        "type": "status",
        "message": "ready",
        "session_id": session_id,
    })

    try:
        while session.is_active:
            # Receive message (binary audio or text command)
            message = await websocket.receive()

            if "bytes" in message:
                # Binary audio chunk
                audio_bytes = message["bytes"]

                async def on_word_score(event: WordScoreEvent):
                    await websocket.send_json({
                        "type": "word_score",
                        "word": event.word,
                        "index": event.index,
                        "score": event.score,
                        "issue": event.issue,
                        "timestamp": event.timestamp,
                        "latency_ms": event.latency_ms,
                    })

                await process_audio_chunk(session, audio_bytes, on_word_score)

            elif "text" in message:
                text = message["text"]

                if text.upper() == "END":
                    # Client finished recording
                    session.is_active = False

                    # Send session summary
                    total_words = len(session.all_word_events)
                    if total_words > 0:
                        overall_score = sum(e.score for e in session.all_word_events) / total_words
                        avg_latency = sum(e.latency_ms for e in session.all_word_events) / total_words
                    else:
                        overall_score = 0.0
                        avg_latency = 0.0

                    await websocket.send_json({
                        "type": "session_end",
                        "total_words": total_words,
                        "overall_score": round(overall_score, 1),
                        "avg_latency_ms": round(avg_latency, 0),
                        "duration_seconds": round(session.buffer_duration, 1),
                    })

                    logger.info(
                        "ws_practice_ended",
                        session=session_id,
                        words=total_words,
                        overall=round(overall_score, 1),
                        avg_latency_ms=round(avg_latency, 0),
                        duration=round(session.buffer_duration, 1),
                    )

            elif "type" in message and message["type"] == "websocket.disconnect":
                break

    except WebSocketDisconnect:
        # Connection dropped — save buffer for batch fallback
        logger.warning(
            "ws_practice_disconnected",
            session=session_id,
            buffer_duration=round(session.buffer_duration, 1),
            words_scored=session.words_scored,
        )

        if session.buffer_duration >= 3.0:
            saved_path = save_buffer_for_fallback(session)
            if saved_path:
                logger.info(
                    "ws_practice_fallback_saved",
                    session=session_id,
                    path=saved_path,
                )

    except Exception as exc:
        logger.error(
            "ws_practice_error",
            session=session_id,
            error=str(exc),
            exc_info=True,
        )
        try:
            await websocket.send_json({
                "type": "error",
                "message": "An error occurred during streaming scoring.",
            })
        except Exception:
            pass

    finally:
        logger.info("ws_practice_closed", session=session_id)
