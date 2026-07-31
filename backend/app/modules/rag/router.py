"""
RAG assistant router.

  POST /assistant/ask — ask a question about the app
  GET  /assistant/suggestions — get proactive pronunciation guidance (Phase 29)
"""

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import Identity, get_current_identity
from app.modules.rag import service
from app.modules.rag.contextual_trigger import get_contextual_suggestions
from app.modules.rag.schemas import AskRequest, AskResponse

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask a question about the app (RAG-grounded)",
)
async def ask(body: AskRequest) -> AskResponse:
    """
    Answers ONLY questions about the AccentIQ app itself.
    Grounded in the knowledge base. Refuses out-of-scope questions.
    """
    return await service.ask_assistant(body.question)


@router.get(
    "/suggestions",
    summary="Get proactive pronunciation suggestions based on error history",
)
async def get_suggestions(
    identity: Identity = Depends(get_current_identity),
) -> dict:
    """
    Phase 29: Returns contextual pronunciation guidance based on the user's
    recurring weak phonemes across sessions. Ties the RAG assistant into
    the user's actual scoring data.

    Returns suggestions with practice words, minimal pairs, and articulation
    guidance targeted at the specific phonemes the user struggles with.
    """
    user_id = identity.user_id if identity.is_authenticated else None
    anon_session_id = identity.anon_session_id

    suggestions = await get_contextual_suggestions(
        user_id=user_id,
        anon_session_id=anon_session_id,
    )

    return {
        "suggestions": suggestions,
        "count": len(suggestions),
        "message": (
            "Based on your recent recordings, here are areas to focus on."
            if suggestions
            else "Keep recording to get personalized suggestions!"
        ),
    }
