"""
Compliance service — DPDP consent recording and checking.

Design decisions:
  - Every consent action appends a new row (audit trail — never updated/deleted).
  - Checking consent for audio processing is enforced as a dependency in Phase 3's
    upload endpoint — callers that bypass it get a 403.
  - consent_type values follow a controlled vocabulary defined in the schema.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.core.logging import get_logger
from app.core.settings import settings
from app.modules.auth.dependencies import Identity
from app.modules.compliance.models import ConsentEvent
from app.modules.compliance.schemas import ConsentEventOut, ConsentStatusResponse

logger = get_logger(__name__)


async def record_consent(
    identity: Identity,
    consent_type: str,
    db: AsyncSession,
) -> ConsentEventOut:
    """
    Append a consent event for the current identity.
    Both authenticated and anonymous callers can consent.
    """
    event = ConsentEvent(
        user_id=identity.user_id,
        anon_session_id=identity.anon_session_id if not identity.is_authenticated else None,
        consent_type=consent_type,
        policy_version=settings.privacy_policy_version,
    )
    db.add(event)
    await db.flush()

    logger.info(
        "consent_recorded",
        identity=identity.display_name,
        consent_type=consent_type,
        policy_version=settings.privacy_policy_version,
    )
    return ConsentEventOut.model_validate(event)


async def get_consent_status(
    identity: Identity,
    db: AsyncSession,
) -> ConsentStatusResponse:
    """Return which consents the current identity has already granted."""
    events = await _get_identity_consents(identity, db)
    consented_types = {e.consent_type for e in events}
    return ConsentStatusResponse(
        has_audio_processing_consent="audio_processing" in consented_types,
        has_privacy_policy_consent="privacy_policy" in consented_types,
        policy_version=settings.privacy_policy_version,
    )


async def require_audio_processing_consent(
    identity: Identity,
    db: AsyncSession,
) -> None:
    """
    Dependency-style guard: raises AuthorizationError if audio_processing
    consent has not been recorded for this identity.
    Used in Phase 3's upload endpoint so consent cannot be bypassed.
    """
    events = await _get_identity_consents(identity, db)
    consented_types = {e.consent_type for e in events}

    if "audio_processing" not in consented_types:
        raise AuthorizationError(
            message=(
                "You must consent to audio processing before uploading recordings. "
                "Please accept the privacy policy and consent checkbox first."
            ),
            details={"missing_consent": "audio_processing"},
        )


# ── Private helpers ───────────────────────────────────────────────────────────

async def _get_identity_consents(
    identity: Identity,
    db: AsyncSession,
) -> list[ConsentEvent]:
    """Fetch all consent events for the current identity."""
    if identity.is_authenticated and identity.user_id:
        result = await db.execute(
            select(ConsentEvent).where(ConsentEvent.user_id == identity.user_id)
        )
    elif identity.anon_session_id:
        result = await db.execute(
            select(ConsentEvent).where(
                ConsentEvent.anon_session_id == identity.anon_session_id
            )
        )
    else:
        return []

    return list(result.scalars().all())
