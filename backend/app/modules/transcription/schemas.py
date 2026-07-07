"""
Pydantic schemas for the transcription module.

Includes both the API response schemas and the Mongo document shape
(validated via Pydantic even though it's stored in MongoDB).
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ── Mongo document schema (validated before write) ────────────────────────────

class WordSegment(BaseModel):
    """A single word with forced-alignment timestamps."""
    word: str
    start: float  # seconds from recording start
    end: float
    confidence: float = Field(ge=0.0, le=1.0)


class TranscriptDocument(BaseModel):
    """
    Full transcript stored in MongoDB `transcripts` collection.
    Validated via Pydantic before insert — ensures shape consistency.
    """
    id: str = Field(alias="_id")
    recording_id: str
    raw_text: str
    words: list[WordSegment]
    language: str = "en"
    model_version: str = ""
    created_at: datetime

    model_config = {"populate_by_name": True, "protected_namespaces": ()}


# ── API response schemas ──────────────────────────────────────────────────────

class RecordingStatusResponse(BaseModel):
    """Returned by the polling endpoint."""
    recording_id: str
    status: str  # uploaded | processing | scored | failed
    error_reason: str | None = None
    duration_seconds: float
    created_at: datetime

    model_config = {"from_attributes": True}


class TranscriptResponse(BaseModel):
    """Full transcript returned to the frontend after processing completes."""
    recording_id: str
    raw_text: str
    words: list[WordSegment]
    language: str
    model_version: str
