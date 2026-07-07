"""
Practice generator service.

Flow:
  1. Aggregate weak phonemes from recent recordings
  2. Check if today's practice set is already cached (Mongo)
  3. If not cached: generate via Gemini → validate → cache
  4. Return the practice set

Validation: re-run phonemizer on generated sentences to confirm
they actually contain the target phonemes. Retry up to MAX_RETRIES
if validation fails (capped — never infinite loop).
"""

import json
from datetime import UTC, datetime, date

from app.core.logging import get_logger
from app.core.settings import settings
from app.db.mongo.client import get_mongo_db
from app.modules.auth.dependencies import Identity
from app.modules.feedback.openrouter_client import call_openrouter
from app.modules.practice_generator.prompt_templates import (
    SYSTEM_PROMPT,
    build_practice_prompt,
    get_fallback_sentences,
)
from app.modules.practice_generator.schemas import PracticeSetResponse, PracticeSentence
from app.modules.practice_generator.weak_phoneme_aggregator import (
    aggregate_from_recording_ids,
    get_recent_recording_ids_for_user,
)
from app.modules.scoring.phoneme_compare import get_reference_phonemes

logger = get_logger(__name__)

COLLECTION = "practice_sets"
MAX_RETRIES = 2  # max LLM regeneration attempts if validation fails


async def get_today_practice(identity: Identity) -> PracticeSetResponse:
    """
    Get or generate today's practice set for this identity.
    Stable within a day (cached per user/date).
    """
    today = date.today().isoformat()
    identity_key = _identity_key(identity)

    # 1. Check cache
    cached = await _get_cached_set(identity_key, today)
    if cached:
        return PracticeSetResponse(
            weak_phonemes=cached["weak_phonemes"],
            sentences=[PracticeSentence(**s) for s in cached["sentences"]],
            date=today,
            generated_at=cached.get("generated_at"),
            is_cached=True,
        )

    # 2. Aggregate weak phonemes
    recording_ids = await get_recent_recording_ids_for_user(identity)
    weak_phonemes = await aggregate_from_recording_ids(recording_ids)

    if not weak_phonemes:
        # No data yet — return empty practice set
        return PracticeSetResponse(
            weak_phonemes=[],
            sentences=[],
            date=today,
            is_cached=False,
        )

    # 3. Generate sentences
    sentences = await _generate_validated_sentences(weak_phonemes)

    # 4. Cache the result
    await _cache_practice_set(identity_key, today, weak_phonemes, sentences)

    return PracticeSetResponse(
        weak_phonemes=weak_phonemes,
        sentences=sentences,
        date=today,
        generated_at=datetime.now(UTC),
        is_cached=False,
    )


async def regenerate_practice(identity: Identity) -> PracticeSetResponse:
    """
    Force regeneration (bypasses cache) — user clicked "give me new sentences".
    Overwrites today's cached set.
    """
    today = date.today().isoformat()
    identity_key = _identity_key(identity)

    # Aggregate phonemes
    recording_ids = await get_recent_recording_ids_for_user(identity)
    weak_phonemes = await aggregate_from_recording_ids(recording_ids)

    if not weak_phonemes:
        return PracticeSetResponse(
            weak_phonemes=[], sentences=[], date=today, is_cached=False
        )

    # Generate fresh sentences (skip cache)
    sentences = await _generate_validated_sentences(weak_phonemes)

    # Overwrite cache
    await _cache_practice_set(identity_key, today, weak_phonemes, sentences)

    return PracticeSetResponse(
        weak_phonemes=weak_phonemes,
        sentences=sentences,
        date=today,
        generated_at=datetime.now(UTC),
        is_cached=False,
    )


# ── Private helpers ───────────────────────────────────────────────────────────

def _identity_key(identity: Identity) -> str:
    """Deterministic key scoping the practice set to a user/session."""
    if identity.is_authenticated and identity.user_id:
        return f"user:{identity.user_id}"
    if identity.anon_session_id:
        return f"anon:{identity.anon_session_id}"
    return "unknown"


async def _get_cached_set(identity_key: str, date_str: str) -> dict | None:
    """Look up today's practice set from Mongo."""
    db = get_mongo_db()
    return await db[COLLECTION].find_one({
        "identity_key": identity_key,
        "date": date_str,
    })


async def _cache_practice_set(
    identity_key: str,
    date_str: str,
    weak_phonemes: list[str],
    sentences: list[PracticeSentence],
) -> None:
    """Persist the practice set (upsert by identity+date)."""
    db = get_mongo_db()
    doc = {
        "identity_key": identity_key,
        "date": date_str,
        "weak_phonemes": weak_phonemes,
        "sentences": [s.model_dump() for s in sentences],
        "generated_at": datetime.now(UTC),
    }
    await db[COLLECTION].replace_one(
        {"identity_key": identity_key, "date": date_str},
        doc,
        upsert=True,
    )
    logger.info("practice_set_cached", identity=identity_key, date=date_str)


async def _generate_validated_sentences(
    weak_phonemes: list[str],
) -> list[PracticeSentence]:
    """
    Generate sentences via LLM with phonemic validation.
    Retries up to MAX_RETRIES if validation fails.
    Falls back to static sentences if LLM is unavailable.
    """
    for attempt in range(MAX_RETRIES + 1):
        sentences = await _call_llm_for_sentences(weak_phonemes)

        if sentences is None:
            # LLM unavailable — use fallback immediately
            logger.warning("practice_using_fallback", reason="llm_unavailable")
            return _build_fallback(weak_phonemes)

        # Validate: each sentence should contain its target phoneme
        validated = _validate_sentences(sentences, weak_phonemes)

        if validated:
            logger.info(
                "practice_sentences_validated",
                attempt=attempt + 1,
                count=len(validated),
            )
            return validated

        logger.warning(
            "practice_validation_failed",
            attempt=attempt + 1,
            max_retries=MAX_RETRIES,
        )

    # All retries exhausted — fallback
    logger.warning("practice_retries_exhausted", using="fallback")
    return _build_fallback(weak_phonemes)


async def _call_llm_for_sentences(
    weak_phonemes: list[str],
) -> list[PracticeSentence] | None:
    """Call OpenRouter to generate practice sentences. Returns None on failure."""
    user_prompt = build_practice_prompt(weak_phonemes)
    result = await call_openrouter(SYSTEM_PROMPT, user_prompt)

    if result is None:
        return None

    # Parse the response
    raw_sentences = result.get("sentences", [])
    if not raw_sentences or not isinstance(raw_sentences, list):
        return None

    sentences = []
    for item in raw_sentences:
        if isinstance(item, dict) and "text" in item:
            sentences.append(PracticeSentence(
                text=item["text"],
                targets=item.get("targets", []),
            ))

    return sentences if sentences else None


def _validate_sentences(
    sentences: list[PracticeSentence],
    weak_phonemes: list[str],
) -> list[PracticeSentence] | None:
    """
    Validate that each sentence actually contains its target phonemes.
    Uses phonemizer (fallback G2P) to check.
    Returns validated list or None if validation fails.
    """
    validated = []

    for sentence in sentences:
        # Get phonemes for each word in the sentence
        words = sentence.text.split()
        all_phonemes = []
        for word in words:
            all_phonemes.extend(get_reference_phonemes(word))

        phoneme_set = set(all_phonemes)

        # Check if at least one target phoneme is present
        targets_present = any(t in phoneme_set for t in sentence.targets)

        if targets_present or not sentence.targets:
            validated.append(sentence)

    # Accept if at least half passed validation
    if len(validated) >= len(weak_phonemes) * 0.5:
        return validated

    return None


def _build_fallback(weak_phonemes: list[str]) -> list[PracticeSentence]:
    """Build practice sentences from static fallback data."""
    fallback_data = get_fallback_sentences(weak_phonemes)
    return [PracticeSentence(**item) for item in fallback_data]
