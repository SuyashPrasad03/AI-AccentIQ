"""Pydantic schemas for the progress module."""

from datetime import datetime

from pydantic import BaseModel


class ScoreDelta(BaseModel):
    prev: float | None
    curr: float
    delta: float | None  # curr - prev, None if no previous


class PhonemeComparison(BaseModel):
    phoneme: str
    prev: float | None
    curr: float
    delta: float | None


class ComparisonResponse(BaseModel):
    recording_id: str
    has_previous: bool
    overall: ScoreDelta
    fluency: ScoreDelta
    accuracy: ScoreDelta
    per_phoneme: list[PhonemeComparison]


class HistoryEntry(BaseModel):
    recording_id: str
    overall_score: float
    fluency_score: float
    accuracy_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    entries: list[HistoryEntry]
    total: int
