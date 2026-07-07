"""Pydantic schemas for the compliance module."""

from datetime import datetime

from pydantic import BaseModel, Field


class RecordConsentRequest(BaseModel):
    consent_type: str = Field(
        ...,
        description="One of: audio_processing, data_retention, privacy_policy",
        pattern="^(audio_processing|data_retention|privacy_policy)$",
    )


class ConsentEventOut(BaseModel):
    id: str
    consent_type: str
    policy_version: str
    granted_at: datetime

    model_config = {"from_attributes": True}


class ConsentStatusResponse(BaseModel):
    has_audio_processing_consent: bool
    has_privacy_policy_consent: bool
    policy_version: str


class DataSummaryResponse(BaseModel):
    user_id: str
    email: str
    recordings_count: int
    consent_events_count: int
    audio_retention_days: int
    account_created_at: datetime
