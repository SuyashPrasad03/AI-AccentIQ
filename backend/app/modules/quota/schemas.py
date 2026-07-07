"""Pydantic schemas for the quota module."""

from pydantic import BaseModel


class QuotaStatusResponse(BaseModel):
    used: int
    limit: int
    requires_auth: bool
    remaining: int


class IncrementResponse(BaseModel):
    used: int
    limit: int
    remaining: int
    quota_exceeded: bool
