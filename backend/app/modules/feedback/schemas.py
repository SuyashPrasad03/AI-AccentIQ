"""Pydantic schemas for the feedback module."""

from pydantic import BaseModel, Field


class ExplainRequest(BaseModel):
    """Query params for the explain endpoint (word index in the score array)."""
    pass  # word_index comes from the URL path


class ExplainResponse(BaseModel):
    """Structured explanation returned to the frontend."""
    word: str
    detected_issue: str
    explanation: str
    mouth_position_tip: str
    practice_words: list[str] = Field(default_factory=list)
    from_cache: bool = False
