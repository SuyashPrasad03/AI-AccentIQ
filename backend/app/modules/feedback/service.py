"""
Feedback service — evidence-grounded LLM explanation generation.

Phase 27 update:
  - Builds structured evidence from GOP + classifier data
  - Feeds evidence into the LLM prompt (not just word + issue)
  - Verifies generated feedback against evidence (hallucination prevention)
  - Regeneration loop: max 2 retries if verification fails
  - Falls back to safe generic template if verification keeps failing
  - Never shows an unverified specific claim to a user

Flow:
  1. Build evidence from scoring data (GOP raw scores, error types)
  2. Build cache key from (word, issue, substitution)
  3. Check Mongo cache → return if hit
  4. Call OpenRouter/Gemini with evidence-grounded prompt
  5. Verify response against evidence
  6. If verification fails: retry (max 2x) → fallback
  7. Cache verified response for future hits
"""

from app.core.logging import get_logger
from app.core.settings import settings
from app.db.mongo.explanations import (
    build_cache_key,
    get_cached_explanation,
    store_explanation,
)
from app.modules.feedback.evidence_builder import (
    WordEvidence,
    build_word_evidence,
    format_evidence_for_prompt,
)
from app.modules.feedback.feedback_verifier import (
    verify_feedback,
    get_safe_fallback_feedback,
)
from app.modules.feedback.openrouter_client import call_openrouter
from app.modules.feedback.prompt_templates import (
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_LEGACY,
    build_user_prompt,
    get_fallback_explanation,
)
from app.modules.feedback.schemas import ExplainResponse

logger = get_logger(__name__)

MAX_VERIFICATION_RETRIES = 2


async def explain_mistake(
    word: str,
    detected_issue: str,
    expected_phonemes: list[str],
    substituted_as: list[str],
    gop_raw_data: dict | None = None,
    word_data: dict | None = None,
    native_language: str | None = None,
) -> ExplainResponse:
    """
    Get a human-friendly, evidence-grounded explanation for a pronunciation mistake.
    Cache-first, then LLM (with verification), then static fallback.

    Args:
        word: The word text
        detected_issue: Issue classification (mispronounced, unclear, mistimed, correct)
        expected_phonemes: Expected IPA phonemes for this word
        substituted_as: Detected phoneme substitutions
        gop_raw_data: Optional raw GOP data for this word (from MongoDB gop_raw_scores)
        word_data: Optional full word data dict (for error classifier results)
        native_language: Optional user's native language for L1-adaptive feedback
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
            confidence_level=cached.get("confidence_level", "Medium"),
            from_cache=True,
        )

    # 3. Build evidence (Phase 27)
    evidence = None
    evidence_text = None
    if word_data or gop_raw_data:
        wd = word_data or {
            "word": word,
            "word_score": 50.0,
            "detected_issue": detected_issue,
            "expected_phonemes": expected_phonemes,
            "substituted_as": substituted_as,
        }
        evidence = build_word_evidence(wd, gop_raw_data)
        evidence_text = format_evidence_for_prompt(evidence)

    # 3b. Add L1 transfer context if user has native language set (Phase 28)
    if native_language and evidence_text:
        from app.modules.feedback.l1_transfer_patterns import get_l1_feedback_context
        l1_context = get_l1_feedback_context(native_language, expected_phonemes, substituted_as)
        if l1_context:
            evidence_text += "\n" + l1_context

    # 4. Call LLM with evidence-grounded prompt
    system_prompt = SYSTEM_PROMPT if evidence_text else SYSTEM_PROMPT_LEGACY
    user_prompt = build_user_prompt(
        word, detected_issue, expected_phonemes, substituted_as,
        evidence_text=evidence_text,
    )

    # 5. Attempt generation with verification (max retries)
    for attempt in range(MAX_VERIFICATION_RETRIES + 1):
        llm_result = await call_openrouter(system_prompt, user_prompt)

        if not llm_result or not _validate_llm_response(llm_result):
            logger.warning(
                "explain_llm_invalid",
                word=word, attempt=attempt,
            )
            continue

        # 6. Verify against evidence (if we have evidence)
        if evidence:
            feedback_text = (
                llm_result.get("explanation", "") + " " +
                llm_result.get("mouth_position_tip", "")
            )
            verification = verify_feedback(feedback_text, evidence)

            if not verification.is_valid:
                logger.warning(
                    "explain_verification_failed",
                    word=word,
                    attempt=attempt,
                    issues=verification.issues,
                    ungrounded=verification.ungrounded_claims,
                )
                if attempt < MAX_VERIFICATION_RETRIES:
                    continue  # Retry
                else:
                    # Max retries exhausted — use safe fallback
                    logger.warning("explain_using_safe_fallback", word=word)
                    fallback = get_safe_fallback_feedback(evidence)
                    return ExplainResponse(
                        word=word,
                        detected_issue=detected_issue,
                        explanation=fallback["explanation"],
                        mouth_position_tip=fallback["mouth_position_tip"],
                        practice_words=fallback.get("practice_words", []),
                        confidence_level=fallback.get("confidence_level", "Medium"),
                        from_cache=False,
                    )

        # Verification passed (or no evidence to verify against)
        confidence_level = llm_result.get("confidence_level", "Medium")
        if evidence:
            confidence_level = evidence.confidence_level

        # Cache write-through
        await store_explanation(
            cache_key=cache_key,
            explanation=llm_result["explanation"],
            mouth_position_tip=llm_result["mouth_position_tip"],
            practice_words=llm_result.get("practice_words", []),
            model_version=settings.openrouter_model,
            confidence_level=confidence_level,
            evidence_refs=llm_result.get("evidence_refs", []),
        )

        return ExplainResponse(
            word=word,
            detected_issue=detected_issue,
            explanation=llm_result["explanation"],
            mouth_position_tip=llm_result["mouth_position_tip"],
            practice_words=llm_result.get("practice_words", []),
            confidence_level=confidence_level,
            from_cache=False,
        )

    # 7. All attempts failed — use static fallback
    logger.warning("explain_using_static_fallback", word=word, issue=detected_issue)
    fallback = get_fallback_explanation(word, detected_issue, expected_phonemes)

    return ExplainResponse(
        word=word,
        detected_issue=detected_issue,
        explanation=fallback["explanation"],
        mouth_position_tip=fallback["mouth_position_tip"],
        practice_words=fallback["practice_words"],
        confidence_level="Low",
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
