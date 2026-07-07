"""
Tests for the feedback module (Explain My Mistake).

Testing checklist:
- Cache hit path never calls OpenRouter
- Fallback path triggers when OpenRouter fails
- Explanation content validated against expected schema
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.feedback.schemas import ExplainResponse
from app.modules.feedback.service import explain_mistake, _validate_llm_response
from app.modules.feedback.prompt_templates import (
    build_user_prompt,
    get_fallback_explanation,
    SYSTEM_PROMPT,
)
from app.db.mongo.explanations import build_cache_key


# ── Cache key tests ───────────────────────────────────────────────────────────

class TestCacheKey:
    def test_deterministic(self):
        k1 = build_cache_key("think", "mispronounced", ["t", "ɪ", "ŋ", "k"])
        k2 = build_cache_key("think", "mispronounced", ["t", "ɪ", "ŋ", "k"])
        assert k1 == k2

    def test_different_issues_different_keys(self):
        k1 = build_cache_key("think", "mispronounced", ["t"])
        k2 = build_cache_key("think", "unclear", ["t"])
        assert k1 != k2

    def test_case_insensitive_word(self):
        k1 = build_cache_key("Think", "mispronounced", [])
        k2 = build_cache_key("think", "mispronounced", [])
        assert k1 == k2


# ── Prompt template tests ─────────────────────────────────────────────────────

class TestPromptTemplates:
    def test_system_prompt_not_empty(self):
        assert len(SYSTEM_PROMPT) > 100

    def test_user_prompt_mispronounced(self):
        prompt = build_user_prompt("think", "mispronounced", ["θ", "ɪ"], ["t", "ɪ"])
        assert "think" in prompt
        assert "mispronounced" in prompt.lower() or "what went wrong" in prompt.lower()

    def test_user_prompt_unclear(self):
        prompt = build_user_prompt("word", "unclear", ["w", "ɜ"], [])
        assert "unclear" in prompt.lower() or "unclearly" in prompt.lower()

    def test_user_prompt_mistimed(self):
        prompt = build_user_prompt("hello", "mistimed", ["h", "ɛ"], [])
        assert "timing" in prompt.lower() or "pace" in prompt.lower()

    def test_fallback_returns_valid_structure(self):
        fb = get_fallback_explanation("think", "mispronounced", ["θ"])
        assert "explanation" in fb
        assert "mouth_position_tip" in fb
        assert "practice_words" in fb
        assert isinstance(fb["practice_words"], list)


# ── LLM response validation ──────────────────────────────────────────────────

class TestValidation:
    def test_valid_response_passes(self):
        data = {
            "explanation": "You replaced TH with T.",
            "mouth_position_tip": "Put tongue between teeth.",
            "practice_words": ["think", "three"],
        }
        assert _validate_llm_response(data) is True

    def test_missing_explanation_fails(self):
        data = {"mouth_position_tip": "tip"}
        assert _validate_llm_response(data) is False

    def test_empty_explanation_fails(self):
        data = {"explanation": "", "mouth_position_tip": "tip"}
        assert _validate_llm_response(data) is False

    def test_missing_tip_fails(self):
        data = {"explanation": "Something went wrong."}
        assert _validate_llm_response(data) is False


# ── Service integration tests ─────────────────────────────────────────────────

class TestExplainService:
    @pytest.mark.asyncio
    async def test_cache_hit_skips_openrouter(self):
        """When cache has an entry, OpenRouter is NEVER called."""
        cached_doc = {
            "cache_key": "think|mispronounced|t,ɪ,ŋ,k",
            "explanation": "Cached explanation.",
            "mouth_position_tip": "Cached tip.",
            "practice_words": ["think"],
        }

        with (
            patch(
                "app.modules.feedback.service.get_cached_explanation",
                new=AsyncMock(return_value=cached_doc),
            ),
            patch(
                "app.modules.feedback.service.call_openrouter",
                new=AsyncMock(side_effect=AssertionError("Should not be called")),
            ) as mock_llm,
        ):
            result = await explain_mistake(
                word="think",
                detected_issue="mispronounced",
                expected_phonemes=["θ", "ɪ", "ŋ", "k"],
                substituted_as=["t", "ɪ", "ŋ", "k"],
            )

        assert result.from_cache is True
        assert result.explanation == "Cached explanation."
        # OpenRouter was never called (would have raised AssertionError)

    @pytest.mark.asyncio
    async def test_cache_miss_calls_openrouter(self):
        """Cache miss → call OpenRouter → cache write-through."""
        llm_response = {
            "explanation": "LLM generated explanation.",
            "mouth_position_tip": "LLM tip.",
            "practice_words": ["three", "through"],
        }

        with (
            patch(
                "app.modules.feedback.service.get_cached_explanation",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.modules.feedback.service.call_openrouter",
                new=AsyncMock(return_value=llm_response),
            ),
            patch(
                "app.modules.feedback.service.store_explanation",
                new=AsyncMock(),
            ) as mock_store,
        ):
            result = await explain_mistake(
                word="think",
                detected_issue="mispronounced",
                expected_phonemes=["θ"],
                substituted_as=["t"],
            )

        assert result.from_cache is False
        assert result.explanation == "LLM generated explanation."
        mock_store.assert_called_once()

    @pytest.mark.asyncio
    async def test_openrouter_failure_uses_fallback(self):
        """When OpenRouter returns None (failure), use static fallback."""
        with (
            patch(
                "app.modules.feedback.service.get_cached_explanation",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.modules.feedback.service.call_openrouter",
                new=AsyncMock(return_value=None),
            ),
        ):
            result = await explain_mistake(
                word="think",
                detected_issue="mispronounced",
                expected_phonemes=["θ"],
                substituted_as=["t"],
            )

        assert result.from_cache is False
        # Should have the fallback explanation
        assert "common" in result.explanation.lower() or "substituted" in result.explanation.lower()
        assert len(result.mouth_position_tip) > 0
        assert len(result.practice_words) > 0

    @pytest.mark.asyncio
    async def test_invalid_llm_response_uses_fallback(self):
        """When LLM returns invalid JSON shape, fallback instead of crash."""
        bad_response = {"wrong_key": "no good"}

        with (
            patch(
                "app.modules.feedback.service.get_cached_explanation",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.modules.feedback.service.call_openrouter",
                new=AsyncMock(return_value=bad_response),
            ),
        ):
            result = await explain_mistake(
                word="hello",
                detected_issue="unclear",
                expected_phonemes=["h", "ɛ"],
                substituted_as=[],
            )

        # Should get a valid response (from fallback), not crash
        assert isinstance(result, ExplainResponse)
        assert result.explanation != ""
