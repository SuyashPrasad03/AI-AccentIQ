"""
RAG assistant router.

  POST /assistant/ask — ask a question about the app
"""

from fastapi import APIRouter

from app.modules.rag import service
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
