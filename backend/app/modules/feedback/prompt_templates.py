"""
Prompt templates for pronunciation feedback generation.

Phase 27 update:
  - Prompt now receives STRUCTURED EVIDENCE as input (GOP scores, error types)
  - LLM output must reference specific phonemes/words with measured values
  - No generic encouragement — every claim must be grounded in evidence
  - Includes few-shot examples showing grounded vs. generic style

Design:
  - System prompt fixes the tone (encouraging, concise, actionable coach).
  - User prompt provides structured acoustic evidence (never PII/audio).
  - Output schema enforced via JSON mode — frontend expects fixed keys.
  - Evidence references required in output for verification.
"""

SYSTEM_PROMPT = """You are a friendly, evidence-based pronunciation coach. Your job is to explain why a specific English word was mispronounced, grounding EVERY claim in the acoustic measurement data provided.

CRITICAL RULES:
1. ONLY make claims supported by the EVIDENCE DATA below. If the data shows /θ/ was replaced by /t/, you can say that. If it doesn't, you cannot.
2. Reference specific phonemes and measurements from the evidence.
3. Be concise (2-3 sentences per field max) and encouraging.
4. Focus on mouth position, tongue placement, and airflow for the specific sounds identified in the evidence.
5. Provide 3-5 practice words that use the SAME problematic sound identified in the evidence.
6. Include a confidence_level field ("High", "Medium", or "Low") based on the evidence confidence.

Output ONLY valid JSON matching this exact schema:
{
  "explanation": "Evidence-grounded explanation referencing specific measured sounds.",
  "mouth_position_tip": "Specific guidance for the exact sounds identified in the evidence.",
  "practice_words": ["word1", "word2", "word3"],
  "confidence_level": "High|Medium|Low",
  "evidence_refs": ["brief description of which evidence supports each claim"]
}

EXAMPLES OF GOOD (GROUNDED) vs. BAD (GENERIC) FEEDBACK:

GOOD: "The /θ/ sound in 'think' was detected as /t/ (gap=3.2, High confidence). Your tongue needs to come forward between your teeth for the 'th' sound."
BAD: "You might want to practice this word more carefully." (no specific evidence referenced)

GOOD: "Your pronunciation of the /r/ sound scored 2.1 below expected (Medium confidence). Try curling your tongue tip slightly back."
BAD: "Some sounds in this word were unclear." (vague, no measurement referenced)

Do NOT use technical terms like 'GOP' or 'log-posterior' — translate measurements into plain language (e.g., "strong mismatch detected" instead of "gap=4.2")."""


SYSTEM_PROMPT_LEGACY = """You are a friendly, encouraging pronunciation coach. Your job is to explain why a specific English word was mispronounced and provide a clear, actionable tip to fix it.

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
    evidence_text: str | None = None,
) -> str:
    """
    Build the user prompt from structured mistake data.

    Phase 27: If evidence_text is provided, uses the evidence-grounded prompt format.
    Otherwise, falls back to the legacy prompt format.
    """
    if evidence_text:
        return _build_evidence_grounded_prompt(word, detected_issue, evidence_text)
    else:
        return _build_legacy_prompt(word, detected_issue, expected_phonemes, substituted_as)


def _build_evidence_grounded_prompt(
    word: str,
    detected_issue: str,
    evidence_text: str,
) -> str:
    """Build prompt with structured evidence (Phase 27)."""
    return (
        f"Analyze this pronunciation issue using ONLY the evidence data below.\n"
        f"Ground every claim in a specific measurement from the evidence.\n\n"
        f"═══ ACOUSTIC EVIDENCE ═══\n"
        f"{evidence_text}\n"
        f"═════════════════════════\n\n"
        f"Based on this evidence, explain what went wrong with \"{word}\" "
        f"and provide an actionable tip to fix it. "
        f"Every claim must reference something in the evidence above."
    )


def _build_legacy_prompt(
    word: str,
    detected_issue: str,
    expected_phonemes: list[str],
    substituted_as: list[str],
) -> str:
    """Legacy prompt format (pre-Phase 27)."""
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
