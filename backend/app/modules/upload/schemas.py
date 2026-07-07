"""Pydantic schemas for the upload module."""

from datetime import datetime

from pydantic import BaseModel


class RecordingOut(BaseModel):
    id: str
    user_id: str | None
    anon_session_id: str | None
    storage_path: str
    duration_seconds: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    recording: RecordingOut
    message: str
