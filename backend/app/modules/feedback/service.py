"""
Feedback service — cache-first LLM explanation generation.

Flow:
  1. Build cache key from (word, issue, substitution)
  2. Check Mongo cache → return if hit
  3. Call OpenRouter/Gemini → validate response → cache write-through
  4. On LLM failure → return static fallback (never show raw error to learner)
"""

from app.core.logging import get_logger
from app.core.settings import settings
from app.db.mongo.explanations import (
    build_cache_key,
    get_cached_explanation,
    store_explanation,
)
from app.modules.feedback.openrouter_client import call_openrouter
from app.modules.feedback.prompt_templates import (
    SYSTEM_PROMPT,
    build_user_prompt,
    get_fallback_explanation,
)
from app.modules.feedback.schemas import ExplainResponse

logger = get_logger(__name__)


async def explain_mistake(
    word: str,
    detected_issue: str,
    expected_phonemes: list[str],
    substituted_as: list[str],
) -> ExplainResponse:
    """
    Get a human-friendly explanation for a pronunciation mistake.
    Cache-first, then LLM, then static fallback.
    """
    # 1. Build cache key
    cache_key = build_cache_key(word, detected_issue, substituted_as)

    # 2. Check cache
    cached = await get_cached_explanation(cache_key)
    if cached:
        return ExplainResponse(
            word=word,
            detected_issue=detected_issue,
            explanation=cached["explanation"],
            mouth_position_tip=cached["mouth_position_tip"],
            practice_words=cached.get("practice_words", []),
            from_cache=True,
        )

    # 3. Call LLM
    user_prompt = build_user_prompt(word, detected_issue, expected_phonemes, substituted_as)
    llm_result = await call_openrouter(SYSTEM_PROMPT, user_prompt)

    if llm_result and _validate_llm_response(llm_result):
        # Cache write-through
        await store_explanation(
            cache_key=cache_key,
            explanation=llm_result["explanation"],
            mouth_position_tip=llm_result["mouth_position_tip"],
            practice_words=llm_result.get("practice_words", []),
            model_version=settings.openrouter_model,
        )

        return ExplainResponse(
            word=word,
            detected_issue=detected_issue,
            explanation=llm_result["explanation"],
            mouth_position_tip=llm_result["mouth_position_tip"],
            practice_words=llm_result.get("practice_words", []),
            from_cache=False,
        )

    # 4. Fallback (LLM unavailable or invalid response)
    logger.warning("explain_using_fallback", word=word, issue=detected_issue)
    fallback = get_fallback_explanation(word, detected_issue, expected_phonemes)

    return ExplainResponse(
        word=word,
        detected_issue=detected_issue,
        explanation=fallback["explanation"],
        mouth_position_tip=fallback["mouth_position_tip"],
        practice_words=fallback["practice_words"],
        from_cache=False,
    )


def _validate_llm_response(data: dict) -> bool:
    """Validate the LLM response has the required fields."""
    required = ["explanation", "mouth_position_tip"]
    for key in required:
        if key not in data or not isinstance(data[key], str) or not data[key].strip():
            logger.warning("llm_response_invalid", missing_key=key)
            return False
    return True
