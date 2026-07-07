"""
Prompt templates for pronunciation feedback generation.

Design:
  - System prompt fixes the tone (encouraging, concise, actionable coach).
  - User prompt provides ONLY structured phonetic data (never PII/audio).
  - Output schema enforced via JSON mode — frontend expects fixed keys.
"""

SYSTEM_PROMPT = """You are a friendly, encouraging pronunciation coach. Your job is to explain why a specific English word was mispronounced and provide a clear, actionable tip to fix it.

RULES:
- Be concise (2-3 sentences per field max).
- Be encouraging — never judgmental. The learner is making progress.
- Focus on mouth position, tongue placement, and airflow.
- Provide 3-5 practice words that use the same sound.
- Output ONLY valid JSON matching this exact schema:

{
  "explanation": "A brief, friendly explanation of what went wrong.",
  "mouth_position_tip": "Specific guidance on tongue/lip/teeth positioning.",
  "practice_words": ["word1", "word2", "word3"]
}

Do NOT include anything outside this JSON structure.
Do NOT mention technical terms like 'phoneme' or 'IPA' — speak naturally."""


def build_user_prompt(
    word: str,
    detected_issue: str,
    expected_phonemes: list[str],
    substituted_as: list[str],
) -> str:
    """
    Build the user prompt from structured mistake data.
    Never includes PII — only the linguistic/phonetic context.
    """
    expected_str = " ".join(expected_phonemes) if expected_phonemes else "unknown"
    substituted_str = " ".join(substituted_as) if substituted_as else "unknown"

    if detected_issue == "mispronounced":
        return (
            f'The word "{word}" was mispronounced.\n'
            f"Expected sounds: {expected_str}\n"
            f"What was detected instead: {substituted_str}\n"
            f"Please explain what went wrong and how to fix it."
        )
    elif detected_issue == "unclear":
        return (
            f'The word "{word}" was spoken unclearly (low confidence in recognition).\n'
            f"Expected sounds: {expected_str}\n"
            f"Please explain common reasons this word is hard to pronounce clearly "
            f"and give a tip for speaking it more distinctly."
        )
    elif detected_issue == "mistimed":
        return (
            f'The word "{word}" had unusual timing/pace.\n'
            f"Expected sounds: {expected_str}\n"
            f"Please explain how to improve the rhythm and natural pacing of this word."
        )
    else:
        return (
            f'The word "{word}" may need improvement.\n'
            f"Expected sounds: {expected_str}\n"
            f"Please provide general pronunciation guidance for this word."
        )


# ── Static fallback explanations (used when OpenRouter is unavailable) ────────

_FALLBACK_EXPLANATIONS = {
    "mispronounced": {
        "explanation": (
            "It sounds like one or more sounds in this word were substituted "
            "with a similar but different sound. This is very common and fixable with practice."
        ),
        "mouth_position_tip": (
            "Try saying the word slowly, paying attention to where your tongue "
            "touches inside your mouth. Practice in front of a mirror to check "
            "your lip and jaw position."
        ),
        "practice_words": ["the", "think", "that", "three", "through"],
    },
    "unclear": {
        "explanation": (
            "This word wasn't captured clearly. It might have been spoken too "
            "quickly or too softly. That's okay — clarity comes with practice."
        ),
        "mouth_position_tip": (
            "Try over-enunciating the word at first — exaggerate each sound. "
            "Then gradually bring it back to natural speed while keeping each "
            "sound distinct."
        ),
        "practice_words": ["clearly", "speak", "voice", "slowly", "practice"],
    },
    "mistimed": {
        "explanation": (
            "The timing of this word was a bit off — either too fast or too slow "
            "compared to natural English rhythm. Pacing is a subtle skill."
        ),
        "mouth_position_tip": (
            "Listen to a native speaker say this word and tap along to the rhythm. "
            "English has a natural stress pattern — some syllables are longer and "
            "louder than others."
        ),
        "practice_words": ["important", "beautiful", "comfortable", "interesting"],
    },
}


def get_fallback_explanation(
    word: str,
    detected_issue: str,
    expected_phonemes: list[str],
) -> dict:
    """
    Static fallback when OpenRouter is unavailable.
    Returns a dict matching the same schema as the LLM output.
    """
    base = _FALLBACK_EXPLANATIONS.get(detected_issue, _FALLBACK_EXPLANATIONS["unclear"])
    return {
        "explanation": base["explanation"],
        "mouth_position_tip": base["mouth_position_tip"],
        "practice_words": base["practice_words"],
    }
