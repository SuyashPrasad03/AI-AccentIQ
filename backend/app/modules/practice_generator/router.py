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


# ── Phase 31: Practice Plan (Agentic Planner) ────────────────────────────────

@router.get(
    "/plan",
    summary="Get the active practice plan (multi-day, adaptive)",
)
async def get_plan(
    identity: Identity = Depends(get_current_identity),
) -> dict:
    """
    Phase 31: Returns the user's active multi-day practice plan.
    The plan is generated from cross-session error history and adapts
    when new recording data arrives.
    """
    from app.modules.practice_generator.practice_planner_agent import get_active_plan

    user_id = identity.user_id if identity.is_authenticated else None
    plan = await get_active_plan(user_id)

    if plan:
        # Remove MongoDB _id field for serialization
        plan.pop("_id", None)
        return {"plan": plan, "has_plan": True}

    return {"plan": None, "has_plan": False, "message": "No active plan. Generate one to get started."}


@router.post(
    "/plan/generate",
    summary="Generate a new adaptive practice plan",
)
async def generate_plan(
    response: Response,
    identity: Identity = Depends(get_current_identity),
) -> dict:
    """
    Phase 31: Generate a structured N-day practice plan based on the user's
    full error history. Supersedes any existing active plan.

    The plan:
    - Targets top 3 priority phonemes (by frequency × severity)
    - Structures practice across 7 days with progressive difficulty
    - Includes checkpoints every 3 days for re-assessment
    - Uses only sentences from the curated bank (deterministic, reviewable)
    - Adapts on re-generation based on new session data
    """
    from app.modules.practice_generator.practice_planner_agent import generate_practice_plan

    identity = _ensure_anon(identity, response)
    user_id = identity.user_id if identity.is_authenticated else None
    anon_session_id = identity.anon_session_id

    plan = await generate_practice_plan(user_id=user_id, anon_session_id=anon_session_id)

    plan_dict = plan.to_dict()
    plan_dict.pop("_id", None)

    return {
        "plan": plan_dict,
        "has_plan": True,
        "message": f"Generated a {plan.duration_days}-day plan targeting: {', '.join(plan.target_phonemes)}",
    }
