"""
IPA phoneme distance and comparison logic.

Design:
  - Phonemizer (espeak-ng) generates the reference/expected phoneme sequence.
  - We compare expected phonemes against "detected" phonemes derived from
    confidence-proxy heuristics (not full acoustic phoneme recognition —
    that's the "next week" upgrade with wav2vec2-lv-60-espeak-cv-ft).
  - Distance is weighted by phonetic feature similarity: /θ/→/t/ is a smaller
    error than /θ/→/m/ because they share place of articulation.

Phonemizer fallback:
  If phonemizer/espeak-ng isn't installed, returns a heuristic IPA mapping.
"""

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Phonetic feature distance matrix (common substitution pairs) ──────────────
# Lower score = more similar (less severe error)
# These cover the most common L2 English pronunciation errors.
_SUBSTITUTION_SEVERITY = {
    # Dental/alveolar confusions (very common for non-native speakers)
    ("θ", "t"): 0.3,    # "think" → "tink"
    ("θ", "s"): 0.4,    # "think" → "sink"
    ("ð", "d"): 0.3,    # "this" → "dis"
    ("ð", "z"): 0.4,    # "this" → "zis"
    # Liquid confusions
    ("r", "l"): 0.4,    # common in East Asian L1
    ("l", "r"): 0.4,
    # Fricative confusions
    ("v", "w"): 0.3,    # common in Indian English
    ("w", "v"): 0.3,
    ("f", "p"): 0.4,
    ("z", "s"): 0.3,
    ("ʒ", "ʃ"): 0.2,
    ("ʃ", "s"): 0.4,
    # Vowel confusions (less severe — vowels are inherently variable)
    ("æ", "ɛ"): 0.2,
    ("ɪ", "iː"): 0.2,
    ("ʊ", "uː"): 0.2,
    ("ɒ", "ɔː"): 0.2,
    ("ʌ", "ɑː"): 0.3,
}

# Default severity for unknown substitution pairs
_DEFAULT_SEVERITY = 0.6


def get_reference_phonemes(word: str) -> list[str]:
    """
    Get the expected/canonical IPA phonemes for a word using Phonemizer.
    Falls back to a simple heuristic mapping if phonemizer isn't installed.

    Returns a list of IPA characters (each element is one phoneme).
    """
    try:
        from phonemizer import phonemize
        from phonemizer.backend import EspeakBackend

        # Use espeak-ng backend for IPA output
        result = phonemize(
            word.lower().strip(),
            language="en-us",
            backend="espeak",
            strip=True,
            preserve_punctuation=False,
        )
        # Split into individual phonemes (each IPA char)
        phonemes = [ch for ch in result if ch.strip()]
        if phonemes:
            return phonemes

    except (ImportError, Exception) as exc:
        logger.debug("phonemizer_unavailable", word=word, error=str(exc))

    # Fallback: return a basic grapheme-to-phoneme approximation
    return _fallback_g2p(word)


def _fallback_g2p(word: str) -> list[str]:
    """
    Very basic grapheme-to-phoneme for when phonemizer isn't installed.
    Maps common English letter patterns to approximate IPA.
    Not accurate — just enough for the scoring pipeline to function.
    """
    _MAP = {
        "th": "θ", "sh": "ʃ", "ch": "tʃ", "ng": "ŋ",
        "ph": "f", "wh": "w", "ck": "k", "ee": "iː",
        "oo": "uː", "ou": "aʊ", "oi": "ɔɪ", "ai": "eɪ",
    }
    word = word.lower().strip()
    phonemes = []
    i = 0
    while i < len(word):
        # Try digraphs first
        if i + 1 < len(word) and word[i:i+2] in _MAP:
            phonemes.append(_MAP[word[i:i+2]])
            i += 2
        else:
            # Single character mapping
            ch = word[i]
            simple = {
                "a": "æ", "e": "ɛ", "i": "ɪ", "o": "ɒ", "u": "ʌ",
                "b": "b", "c": "k", "d": "d", "f": "f", "g": "ɡ",
                "h": "h", "j": "dʒ", "k": "k", "l": "l", "m": "m",
                "n": "n", "p": "p", "q": "k", "r": "r", "s": "s",
                "t": "t", "v": "v", "w": "w", "x": "ks", "y": "j",
                "z": "z",
            }
            if ch in simple:
                phonemes.append(simple[ch])
            i += 1
    return phonemes if phonemes else ["?"]


def compute_phoneme_distance(expected: list[str], detected: list[str]) -> float:
    """
    Compute a normalized distance between two phoneme sequences.
    Uses weighted Levenshtein where substitution costs come from
    the phonetic feature similarity table.

    Returns a float in [0.0, 1.0] where 0 = identical, 1 = maximally different.
    """
    if not expected and not detected:
        return 0.0
    if not expected or not detected:
        return 1.0

    n = len(expected)
    m = len(detected)

    # Dynamic programming table
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        dp[i][0] = i * 1.0  # deletion cost
    for j in range(m + 1):
        dp[0][j] = j * 1.0  # insertion cost

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if expected[i-1] == detected[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                sub_cost = _get_substitution_cost(expected[i-1], detected[j-1])
                dp[i][j] = min(
                    dp[i-1][j] + 1.0,      # deletion
                    dp[i][j-1] + 1.0,       # insertion
                    dp[i-1][j-1] + sub_cost,  # substitution
                )

    max_len = max(n, m)
    return min(dp[n][m] / max_len, 1.0)


def identify_substitutions(
    expected: list[str], detected: list[str]
) -> list[str]:
    """
    Identify which phonemes were substituted by aligning the sequences.
    Returns the "detected as" phoneme sequence (same length as expected,
    with substitutions in place, '∅' for deletions).
    """
    if not expected:
        return detected or []

    # Simple alignment: match by position (good enough for single words)
    result = []
    for i, exp_ph in enumerate(expected):
        if i < len(detected):
            result.append(detected[i])
        else:
            result.append("∅")  # deletion
    return result


def _get_substitution_cost(a: str, b: str) -> float:
    """Look up the phonetic-feature-weighted substitution cost."""
    if (a, b) in _SUBSTITUTION_SEVERITY:
        return _SUBSTITUTION_SEVERITY[(a, b)]
    if (b, a) in _SUBSTITUTION_SEVERITY:
        return _SUBSTITUTION_SEVERITY[(b, a)]
    return _DEFAULT_SEVERITY
