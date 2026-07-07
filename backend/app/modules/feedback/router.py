"""
Feedback router — explain-my-mistake endpoint.

  GET /recordings/{recording_id}/words/{word_index}/explain
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.db.mongo.phoneme_analysis import get_phoneme_analysis
from app.db.mysql.base import get_db
from app.modules.auth.dependencies import Identity, get_current_identity
from app.modules.feedback import service
from app.modules.feedback.schemas import ExplainResponse
from app.modules.upload.models import Recording

router = APIRouter(prefix="/recordings", tags=["feedback"])


@router.get(
    "/{recording_id}/words/{word_index}/explain",
    response_model=ExplainResponse,
    summary="Get AI explanation for a mispronounced word",
)
async def explain_word(
    recording_id: str,
    word_index: int,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> ExplainResponse:
    """
    Returns a coach-like explanation for why a specific word was flagged.
    Triggered on-demand (per word click) — not pre-generated for all words.

    Uses cache-first lookup, then LLM, then static fallback.
    Never returns a raw error to the learner.
    """
    # 1. Authorization: verify recording ownership
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

    # 2. Fetch the phoneme analysis from Mongo
    analysis = await get_phoneme_analysis(recording_id)
    if analysis is None:
        raise NotFoundError(
            message="Score not yet available. Recording may still be processing."
        )

    words = analysis.get("words", [])
    if word_index < 0 or word_index >= len(words):
        raise ValidationError(
            message=f"Word index {word_index} is out of range (0-{len(words)-1}).",
            details={"word_index": word_index, "total_words": len(words)},
        )

    word_data = words[word_index]
    word_text = word_data.get("word", "")
    detected_issue = word_data.get("detected_issue", "unclear")
    expected_phonemes = word_data.get("expected_phonemes", [])
    substituted_as = word_data.get("substituted_as", [])

    # 3. Get explanation (cache → LLM → fallback)
    return await service.explain_mistake(
        word=word_text,
        detected_issue=detected_issue,
        expected_phonemes=expected_phonemes,
        substituted_as=substituted_as,
    )
