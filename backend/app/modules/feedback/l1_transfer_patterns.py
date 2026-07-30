"""
Phase 28 — L1 Transfer Pattern Table

Curated table of known native-language → English pronunciation transfer patterns.
These are well-documented patterns from applied linguistics research.

When a detected pronunciation error matches a known L1 transfer pattern,
feedback can explain WHY the error is happening (L1 interference) rather
than just stating THAT it happened. This is both more accurate and more
empathetic.

Sources:
  - Swan & Smith (2001). "Learner English" (Cambridge University Press)
  - Avery & Ehrlich (1992). "Teaching American English Pronunciation" (OUP)
  - Brown (2014). "Pronunciation and Phonetics" (Routledge)
  - Kenworthy (1987). "Teaching English Pronunciation" (Longman)

Design:
  - Patterns are indexed by (native_language, expected_phoneme, substituted_phoneme)
  - Each pattern has a human-readable explanation of WHY it happens
  - Optional tip that's specific to the L1 background
  - Pattern matching is phoneme-level, not word-level
"""

from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class L1TransferPattern:
    """A single known L1 transfer pattern."""
    native_language: str
    expected_phoneme: str  # What should be produced
    common_substitution: str  # What L1 speakers typically produce instead
    explanation: str  # WHY this happens (L1 interference reason)
    tip: str  # How to fix it, given the L1 background
    severity: str  # "low" | "medium" | "high" (how much it affects intelligibility)


# ═══════════════════════════════════════════════════════════════════════════════
# CURATED L1 TRANSFER PATTERNS
# Covering: Hindi, Mandarin, Spanish, Arabic, Japanese (5 languages)
# ═══════════════════════════════════════════════════════════════════════════════

L1_PATTERNS: list[L1TransferPattern] = [
    # ── HINDI ────────────────────────────────────────────────────────────────
    L1TransferPattern(
        native_language="hindi",
        expected_phoneme="θ",
        common_substitution="t",
        explanation=(
            "This is a very common pattern for Hindi speakers. Hindi doesn't have "
            "the 'th' (/θ/) sound, so speakers naturally use the closest Hindi sound, "
            "which is a dental /t/. This is called L1 transfer."
        ),
        tip=(
            "Place your tongue TIP between your upper and lower teeth (not behind them). "
            "Blow air gently through the gap. Hindi /t/ is made with the tongue behind "
            "the teeth — English /θ/ is made with the tongue between them."
        ),
        severity="medium",
    ),
    L1TransferPattern(
        native_language="hindi",
        expected_phoneme="ð",
        common_substitution="d",
        explanation=(
            "Hindi speakers often replace the voiced 'th' (/ð/) with /d/ because "
            "Hindi has dental /d/ but no interdental fricative. 'This' becomes 'dis'."
        ),
        tip=(
            "Same tongue position as /θ/ (between the teeth), but add voicing — "
            "you should feel vibration in your throat."
        ),
        severity="medium",
    ),
    L1TransferPattern(
        native_language="hindi",
        expected_phoneme="v",
        common_substitution="w",
        explanation=(
            "Hindi speakers often use /w/ instead of /v/ because in Hindi, "
            "the /v/ sound is much softer and closer to /w/ than English /v/. "
            "This is one of the most recognizable features of Indian English."
        ),
        tip=(
            "Bite your lower lip GENTLY with your upper teeth, then push air through. "
            "English /v/ requires teeth-on-lip contact, while Hindi /v/ doesn't."
        ),
        severity="low",
    ),
    L1TransferPattern(
        native_language="hindi",
        expected_phoneme="z",
        common_substitution="s",
        explanation=(
            "Hindi speakers sometimes devoice /z/ to /s/, especially at word endings. "
            "This is because Hindi rarely uses /z/ in native words."
        ),
        tip="Keep your throat vibrating (voicing) throughout the /z/ sound. "
            "Place your hand on your throat to feel the buzzing.",
        severity="low",
    ),

    # ── MANDARIN CHINESE ─────────────────────────────────────────────────────
    L1TransferPattern(
        native_language="mandarin",
        expected_phoneme="θ",
        common_substitution="s",
        explanation=(
            "Mandarin Chinese doesn't have the /θ/ sound at all. Mandarin speakers "
            "often substitute /s/ because it's the closest fricative in their sound system. "
            "'Think' may become 'sink'."
        ),
        tip=(
            "Move your tongue forward from the /s/ position — it should stick out "
            "slightly between your teeth. The airflow should feel more spread out "
            "than for /s/."
        ),
        severity="medium",
    ),
    L1TransferPattern(
        native_language="mandarin",
        expected_phoneme="r",
        common_substitution="l",
        explanation=(
            "Mandarin doesn't distinguish /r/ and /l/ the same way English does. "
            "Some Mandarin speakers interchange them, particularly in certain positions."
        ),
        tip=(
            "For English /r/: curl your tongue tip back WITHOUT touching the roof. "
            "For /l/: touch the ridge behind your upper teeth. The key difference is "
            "whether your tongue TOUCHES or DOESN'T touch."
        ),
        severity="high",
    ),
    L1TransferPattern(
        native_language="mandarin",
        expected_phoneme="n",
        common_substitution="l",
        explanation=(
            "Some Mandarin dialects merge /n/ and /l/ in certain positions. "
            "This is especially common in southern Chinese dialects."
        ),
        tip=(
            "For /n/: air flows through your NOSE (pinch your nose to check — "
            "you should feel pressure). For /l/: air flows around the SIDES of your tongue."
        ),
        severity="medium",
    ),
    L1TransferPattern(
        native_language="mandarin",
        expected_phoneme="ŋ",
        common_substitution="n",
        explanation=(
            "Mandarin speakers sometimes replace the 'ng' sound (/ŋ/) at the end "
            "of words with /n/. 'Singing' may become 'sinnin'."
        ),
        tip=(
            "The /ŋ/ sound is made at the BACK of your mouth (like when you say 'sing' "
            "and hold the last sound). The /n/ is at the FRONT. Feel where the back "
            "of your tongue touches the soft palate."
        ),
        severity="low",
    ),

    # ── SPANISH ──────────────────────────────────────────────────────────────
    L1TransferPattern(
        native_language="spanish",
        expected_phoneme="v",
        common_substitution="b",
        explanation=(
            "Spanish doesn't distinguish /v/ and /b/ — they're the same phoneme "
            "(an allophone). Spanish speakers often use /b/ where English needs /v/. "
            "'Very' may sound like 'berry'."
        ),
        tip=(
            "For English /v/: your UPPER TEETH must touch your LOWER LIP. "
            "For /b/: both lips come together. Practice: 'vat' vs 'bat' — "
            "feel the difference in lip position."
        ),
        severity="high",
    ),
    L1TransferPattern(
        native_language="spanish",
        expected_phoneme="z",
        common_substitution="s",
        explanation=(
            "Spanish rarely uses /z/ — most speakers produce /s/ in all positions. "
            "'Zip' may sound like 'sip'. This is because Spanish 's' and 'z' "
            "are both voiceless."
        ),
        tip=(
            "Add voicing (throat vibration) to your /s/ sound to produce /z/. "
            "Hold your hand on your throat: 'sss' = no vibration, 'zzz' = vibration."
        ),
        severity="medium",
    ),
    L1TransferPattern(
        native_language="spanish",
        expected_phoneme="dʒ",
        common_substitution="j",
        explanation=(
            "Spanish speakers may pronounce English 'j' (/dʒ/) more like "
            "Spanish 'y' or a softer fricative. 'Judge' may sound more like 'yudge'."
        ),
        tip=(
            "English /dʒ/ starts with your tongue pressed against the roof, "
            "then releases with a 'zh' sound. It's a STOP + FRICATIVE combined."
        ),
        severity="medium",
    ),

    # ── ARABIC ───────────────────────────────────────────────────────────────
    L1TransferPattern(
        native_language="arabic",
        expected_phoneme="p",
        common_substitution="b",
        explanation=(
            "Arabic doesn't have /p/ as a distinct phoneme — it only has /b/. "
            "Arabic speakers often struggle to distinguish 'pat' from 'bat' "
            "or produce a weakly aspirated /p/."
        ),
        tip=(
            "Hold a tissue in front of your mouth. For /p/, you should see a strong "
            "PUFF of air that moves the tissue. For /b/, the tissue barely moves. "
            "Exaggerate the puff at first."
        ),
        severity="high",
    ),
    L1TransferPattern(
        native_language="arabic",
        expected_phoneme="v",
        common_substitution="f",
        explanation=(
            "Many Arabic dialects don't distinguish /v/ from /f/ — both are voiceless "
            "labiodental fricatives. 'Van' may sound like 'fan'."
        ),
        tip=(
            "Same lip position for both /f/ and /v/ (teeth on lower lip). "
            "The ONLY difference is voicing: feel your throat vibrate for /v/, "
            "not for /f/."
        ),
        severity="medium",
    ),

    # ── JAPANESE ─────────────────────────────────────────────────────────────
    L1TransferPattern(
        native_language="japanese",
        expected_phoneme="r",
        common_substitution="l",
        explanation=(
            "Japanese has a single 'r-like' sound (a flap) that's between English "
            "/r/ and /l/. Japanese speakers often can't reliably distinguish or "
            "produce the difference. 'Right' and 'light' may sound the same."
        ),
        tip=(
            "For /r/: tongue curls back, does NOT touch anything. "
            "For /l/: tongue tip touches the ridge behind upper teeth. "
            "Practice minimal pairs: rice/lice, right/light, read/lead."
        ),
        severity="high",
    ),
    L1TransferPattern(
        native_language="japanese",
        expected_phoneme="θ",
        common_substitution="s",
        explanation=(
            "Japanese doesn't have /θ/ (th). Japanese speakers typically "
            "substitute /s/, making 'think' sound like 'sink'."
        ),
        tip=(
            "Put your tongue between your teeth (not behind them). "
            "The Japanese /s/ keeps the tongue behind the teeth — "
            "English /θ/ pushes it forward between them."
        ),
        severity="medium",
    ),
    L1TransferPattern(
        native_language="japanese",
        expected_phoneme="v",
        common_substitution="b",
        explanation=(
            "Japanese /b/ and English /v/ are often confused because "
            "Japanese doesn't have a labiodental fricative /v/."
        ),
        tip=(
            "Upper teeth must touch your lower lip for /v/. "
            "Japanese /b/ uses both lips — English /v/ uses teeth+lip."
        ),
        severity="medium",
    ),
]

# ── Lookup index ─────────────────────────────────────────────────────────────
# Indexed by (language, expected_phoneme) for fast matching
_PATTERN_INDEX: dict[tuple[str, str], list[L1TransferPattern]] = {}

for pattern in L1_PATTERNS:
    key = (pattern.native_language.lower(), pattern.expected_phoneme)
    if key not in _PATTERN_INDEX:
        _PATTERN_INDEX[key] = []
    _PATTERN_INDEX[key].append(pattern)


# ── Public API ───────────────────────────────────────────────────────────────

SUPPORTED_LANGUAGES = sorted(set(p.native_language for p in L1_PATTERNS))


def find_matching_patterns(
    native_language: str | None,
    expected_phoneme: str,
    substituted_as: str | None = None,
) -> list[L1TransferPattern]:
    """
    Find L1 transfer patterns that match the user's native language and error.

    Args:
        native_language: User's declared native language (or None)
        expected_phoneme: The phoneme that should have been produced
        substituted_as: What was actually produced (optional, for exact matching)

    Returns:
        List of matching patterns (may be empty if no match)
    """
    if not native_language:
        return []

    lang = native_language.lower().strip()
    key = (lang, expected_phoneme)
    patterns = _PATTERN_INDEX.get(key, [])

    # If substitution is specified, prefer exact matches
    if substituted_as and patterns:
        exact = [p for p in patterns if p.common_substitution == substituted_as]
        if exact:
            return exact

    return patterns


def get_l1_feedback_context(
    native_language: str | None,
    expected_phonemes: list[str],
    substituted_as: list[str],
) -> str | None:
    """
    Build L1-aware feedback context text for the LLM prompt.
    Returns None if no patterns match (standard feedback applies).
    """
    if not native_language:
        return None

    matched_patterns = []
    for exp, sub in zip(expected_phonemes, substituted_as):
        if exp != sub:
            patterns = find_matching_patterns(native_language, exp, sub)
            matched_patterns.extend(patterns)

    if not matched_patterns:
        return None

    # Build context text
    lines = [f"\nL1 CONTEXT (native language: {native_language}):"]
    for p in matched_patterns[:3]:  # Max 3 patterns per feedback
        lines.append(
            f"  • /{p.expected_phoneme}/ → /{p.common_substitution}/ is a known "
            f"{native_language} transfer pattern: {p.explanation[:100]}..."
        )

    lines.append(
        "\nUse this L1 context to explain WHY the error is happening "
        "(native language interference), not just THAT it happened."
    )

    return "\n".join(lines)
