"""Pydantic schemas for the scoring module."""

from datetime import datetime

from pydantic import BaseModel


class WordScoreOut(BaseModel):
    word: str
    word_score: float
    detected_issue: str  # correct | mispronounced | unclear | mistimed
    expected_phonemes: list[str]
    substituted_as: list[str]
    confidence: float


class ScoreResponse(BaseModel):
    recording_id: str
    overall_score: float
    accuracy_score: float
    fluency_score: float
    word_scores: list[WordScoreOut]
    weak_phonemes: list[str]


class ScoreSummaryOut(BaseModel):
    """Lightweight summary from MySQL (for progress lists)."""
    id: str
    recording_id: str
    overall_score: float
    fluency_score: float
    accuracy_score: float
    created_at: datetime

    model_config = {"from_attributes": True}
