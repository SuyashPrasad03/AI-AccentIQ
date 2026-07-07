"""Pydantic schemas for the RAG assistant module."""

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)


class AskResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)  # source doc names
    refused: bool = False  # True if the question was out-of-scope
