"""
RAG assistant service.

Flow:
  1. Embed the user's question
  2. Retrieve top-k similar chunks from vector index
  3. Check similarity threshold — if below, REFUSE
  4. Build grounded prompt with context
  5. Call OpenRouter/Gemini for answer synthesis
  6. Return answer with sources (or refusal)
"""

from app.core.logging import get_logger
from app.core.settings import settings
from app.modules.feedback.openrouter_client import call_openrouter
from app.modules.rag.prompt_templates import REFUSAL_MESSAGE, build_rag_prompt
from app.modules.rag.schemas import AskResponse
from app.modules.rag.vector_index import search_similar

logger = get_logger(__name__)


async def ask_assistant(question: str) -> AskResponse:
    """
    Answer a question grounded in the KB, or refuse if out-of-scope.
    """
    # 1. Retrieve top-k chunks
    results = await search_similar(question)

    if not results:
        return AskResponse(answer=REFUSAL_MESSAGE, sources=[], refused=True)

    # 2. Check similarity threshold (hard backstop for refusal)
    best_score = results[0]["score"]
    threshold = settings.rag_similarity_threshold

    if best_score < threshold:
        logger.info(
            "rag_refusal_threshold",
            question=question[:80],
            best_score=best_score,
            threshold=threshold,
        )
        return AskResponse(answer=REFUSAL_MESSAGE, sources=[], refused=True)

    # 3. Build context from relevant chunks
    context_chunks = [r["text"] for r in results if r["score"] >= threshold * 0.7]
    sources = list(set(r["source_doc"] for r in results if r["score"] >= threshold * 0.7))

    # 4. Call LLM with grounded prompt
    system_prompt = build_rag_prompt(context_chunks)
    llm_result = await call_openrouter(system_prompt, question)

    if llm_result is None:
        # LLM unavailable — attempt to answer from context directly
        logger.warning("rag_llm_unavailable", using="context_summary")
        answer = _synthesize_from_context(context_chunks, question)
        return AskResponse(answer=answer, sources=sources, refused=False)

    # Parse LLM response
    answer = ""
    if isinstance(llm_result, dict):
        answer = llm_result.get("answer", "") or llm_result.get("response", "")
        if not answer:
            # LLM might have returned plain text in the JSON
            answer = str(llm_result.get("text", ""))
    if isinstance(llm_result, str):
        answer = llm_result

    if not answer.strip():
        answer = _synthesize_from_context(context_chunks, question)

    # 5. Check if LLM itself refused (it's instructed to refuse if context insufficient)
    refusal_indicators = [
        "i don't have information",
        "i can only help with",
        "outside my scope",
        "i cannot answer",
    ]
    is_refused = any(indicator in answer.lower() for indicator in refusal_indicators)

    return AskResponse(
        answer=answer.strip(),
        sources=sources,
        refused=is_refused,
    )


def _synthesize_from_context(chunks: list[str], question: str) -> str:
    """
    Simple fallback when LLM is unavailable:
    return the most relevant chunk text as the answer.
    """
    if not chunks:
        return REFUSAL_MESSAGE
    # Return the first (most relevant) chunk, trimmed
    return chunks[0][:500]
