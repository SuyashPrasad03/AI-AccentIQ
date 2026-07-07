"""
Scoring router — /recordings/{id}/score endpoint.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError
from app.db.mysql.base import get_db
from app.modules.auth.dependencies import Identity, get_current_identity
from app.modules.scoring import service
from app.modules.scoring.schemas import ScoreResponse
from app.modules.upload.models import Recording

router = APIRouter(prefix="/recordings", tags=["scoring"])


@router.get(
    "/{recording_id}/score",
    response_model=ScoreResponse,
    summary="Get pronunciation score and word-level breakdown",
)
async def get_score(
    recording_id: str,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> ScoreResponse:
    """
    Returns the full scoring result:
    - overall_score (0-100)
    - accuracy_score, fluency_score (sub-metrics)
    - word_scores[] with per-word classification and phoneme data
    - weak_phonemes[] for practice generation
    """
    # Authorization: verify ownership
    result = await db.execute(
        select(Recording).where(
            Recording.id == recording_id,
            Recording.deleted_at.is_(None),
        )
    )
    recording = result.scalar_one_or_none()
    if recording is None:
        raise NotFoundError(message="Recording not found.")

    if identity.is_authenticated:
        if recording.user_id != identity.user_id:
            raise AuthorizationError(message="You don't have access to this recording.")
    else:
        if recording.anon_session_id != identity.anon_session_id:
            raise AuthorizationError(message="You don't have access to this recording.")

    # Fetch score
    score = await service.get_score_for_recording(recording_id)
    if score is None:
        raise NotFoundError(
            message="Score not yet available. Recording may still be processing.",
            details={"status": recording.status},
        )
    return score
