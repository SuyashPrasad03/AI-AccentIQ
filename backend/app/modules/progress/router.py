"""
Progress router.

  GET /recordings/{id}/comparison — compare against previous recording
  GET /progress/history           — full score timeline (registered users only)
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, AuthorizationError, NotFoundError
from app.db.mysql.base import get_db
from app.modules.auth.dependencies import Identity, get_current_identity, get_current_user
from app.modules.auth.models import User
from app.modules.progress import service
from app.modules.progress.schemas import ComparisonResponse, HistoryResponse
from app.modules.upload.models import Recording
from sqlalchemy import select

router = APIRouter(tags=["progress"])


@router.get(
    "/recordings/{recording_id}/comparison",
    response_model=ComparisonResponse,
    summary="Compare recording scores against the previous recording",
)
async def get_comparison(
    recording_id: str,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> ComparisonResponse:
    """
    Returns N vs N-1 comparison. Registered users only (needs history).
    Anonymous users get has_previous=False with their single score.
    """
    if not identity.is_authenticated:
        # Anonymous: return current score only, no comparison
        return ComparisonResponse(
            recording_id=recording_id,
            has_previous=False,
            overall=service.ScoreDelta(prev=None, curr=0.0, delta=None),
            fluency=service.ScoreDelta(prev=None, curr=0.0, delta=None),
            accuracy=service.ScoreDelta(prev=None, curr=0.0, delta=None),
            per_phoneme=[],
        )

    # Verify ownership
    result = await db.execute(
        select(Recording).where(
            Recording.id == recording_id,
            Recording.deleted_at.is_(None),
        )
    )
    recording = result.scalar_one_or_none()
    if recording is None:
        raise NotFoundError(message="Recording not found.")
    if recording.user_id != identity.user_id:
        raise AuthorizationError(message="You don't have access to this recording.")

    return await service.get_comparison(recording_id, identity.user_id, db)


@router.get(
    "/progress/history",
    response_model=HistoryResponse,
    summary="Get full score history timeline (registered users only)",
)
async def get_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> HistoryResponse:
    """
    Returns the user's full score timeline for the trend chart.
    Most recent first. Paginated.
    """
    return await service.get_history(
        user_id=current_user.id,
        db=db,
        limit=limit,
        offset=offset,
    )
