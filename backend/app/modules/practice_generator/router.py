"""
Practice generator router.

  GET  /practice/today       — get today's practice set (lazy generate + cache)
  POST /practice/regenerate  — force regeneration of practice sentences
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mysql.base import get_db
from app.modules.auth.dependencies import Identity, get_current_identity
from app.modules.auth.security import generate_anon_session_id, sign_anon_session_id
from app.modules.practice_generator import service
from app.modules.practice_generator.schemas import PracticeSetResponse

router = APIRouter(prefix="/practice", tags=["practice"])

_ANON_COOKIE = "anon_session_id"
_ANON_COOKIE_MAX_AGE = 365 * 24 * 3600


def _ensure_anon(identity: Identity, response: Response) -> Identity:
    if identity.is_authenticated or identity.anon_session_id is not None:
        return identity
    raw_id = generate_anon_session_id()
    signed = sign_anon_session_id(raw_id)
    response.set_cookie(
        key=_ANON_COOKIE, value=signed, httponly=True,
        secure=False, samesite="lax", max_age=_ANON_COOKIE_MAX_AGE, path="/",
    )
    return Identity(user=None, anon_session_id=raw_id)


@router.get(
    "/today",
    response_model=PracticeSetResponse,
    summary="Get today's personalized practice set",
)
async def get_today(
    response: Response,
    identity: Identity = Depends(get_current_identity),
) -> PracticeSetResponse:
    """
    Returns the practice set for today. Lazily generates on first request,
    then cached for the rest of the day. Stable across page reloads.

    Registered users get cross-session aggregation (last 5 recordings).
    Anonymous users get single-recording-based practice.
    """
    identity = _ensure_anon(identity, response)
    return await service.get_today_practice(identity)


@router.post(
    "/regenerate",
    response_model=PracticeSetResponse,
    summary="Generate a new set of practice sentences",
)
async def regenerate(
    response: Response,
    identity: Identity = Depends(get_current_identity),
) -> PracticeSetResponse:
    """
    Explicitly request new sentences. Overwrites today's cached set.
    Use sparingly — helps when a user has already practiced the current set.
    """
    identity = _ensure_anon(identity, response)
    return await service.regenerate_practice(identity)
