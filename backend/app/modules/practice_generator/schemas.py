"""Pydantic schemas for the practice generator module."""

from datetime import datetime

from pydantic import BaseModel


class PracticeSentence(BaseModel):
    text: str
    targets: list[str]


class PracticeSetResponse(BaseModel):
    weak_phonemes: list[str]
    sentences: list[PracticeSentence]
    date: str  # ISO date string (YYYY-MM-DD)
    generated_at: datetime | None = None
    is_cached: bool = False
