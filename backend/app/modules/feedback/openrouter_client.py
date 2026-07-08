"""
OpenRouter / Gemini async client wrapper.

Sends structured prompts to the LLM and returns validated JSON responses.
Never sends PII (audio, email) — only phonetic/linguistic metadata.
"""

import json

import httpx

from app.core.logging import get_logger
from app.core.settings import settings

logger = get_logger(__name__)

_TIMEOUT = 30.0  # seconds


async def call_openrouter(
    system_prompt: str,
    user_prompt: str,
) -> dict | None:
    """
    Call OpenRouter chat completions API with JSON mode.

    Returns the parsed JSON dict from the model's response,
    or None if the call fails (caller handles fallback).
    """
    if not settings.openrouter_api_key:
        logger.warning("openrouter_no_api_key", info="Set OPENROUTER_API_KEY for real LLM feedback")
        return None

    url = f"{settings.openrouter_base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://pronunciation-coach.example.com",
        "X-Title": "Pronunciation Coach",
    }

    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.3,  # low temperature for consistency
        "max_tokens": 500,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            logger.error(
                "openrouter_error",
                status=response.status_code,
                body=response.text[:300],
            )
            return None

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        if not content:
            logger.warning("openrouter_empty_response")
            return None

        # Parse the JSON content from the model
        parsed = json.loads(content)
        logger.info("openrouter_success", model=settings.openrouter_model)
        return parsed

    except json.JSONDecodeError as exc:
        logger.error("openrouter_json_parse_failed", error=str(exc), raw=content[:200])
        return None
    except httpx.TimeoutException:
        logger.error("openrouter_timeout")
        return None
    except Exception as exc:
        logger.error("openrouter_unexpected_error", error=str(exc))
        return None


async def call_openrouter_text(
    system_prompt: str,
    user_prompt: str,
) -> str | None:
    """
    Call OpenRouter WITHOUT JSON mode — returns plain text.
    Used by RAG assistant where we want a natural language answer, not structured JSON.
    """
    if not settings.openrouter_api_key:
        return None

    url = f"{settings.openrouter_base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://pronunciation-coach.example.com",
        "X-Title": "Pronunciation Coach",
    }

    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.5,
        "max_tokens": 500,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            logger.error("openrouter_text_error", status=response.status_code)
            return None

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content.strip() if content else None

    except Exception as exc:
        logger.error("openrouter_text_unexpected_error", error=str(exc))
        return None
