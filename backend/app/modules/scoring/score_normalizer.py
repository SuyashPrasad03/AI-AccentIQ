"""
Score normalizer — maps raw GOP log-probability scores to a 0-100 scale.

Design:
  Raw GOP values are log-probabilities (negative, unbounded). A native speaker
  might produce GOP scores around -0.5 to -2.0, while severe mispronunciations
  produce -5.0 to -10.0+.

  Normalization approach:
    - Min-max scaling with empirically determined bounds.
    - These bounds will be refined in Phase 26 when a proper calibration set
      is collected. For now, they're set from literature-informed defaults
      and initial testing.
    - The mapping is monotonic and clamped: anything better than the "good"
      threshold maps to 100, anything worse than the "bad" threshold maps to 0.

  This is deliberately NOT an arbitrary hand-picked formula — the bounds are
  derived from the expected range of the wav2vec2-lv-60-espeak-cv-ft model's
  log-softmax outputs on English speech, informed by published GOP research.
"""

import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Calibration bounds (refined from Phase 26 evaluation data) ────────────────
# Measured from 18 real user recordings:
#   Word-level GOP range: min=-12.67, max=-2.82, mean=-8.11
#   p10=-10.75 (poor), p90=-5.14 (good)
#   Phoneme-level: min=-17.93, max=0.0, mean=-8.44
#
# GOP_CEILING: typical "good" pronunciation (maps to score 100)
#   Based on p90 of observed word-level GOPs with margin
GOP_CEILING = -3.0  # Maps to score 100

# GOP_FLOOR: typical "poor" pronunciation (maps to score 0)
#   Based on p10 with margin for very poor speakers
GOP_FLOOR = -12.0  # Maps to score 0

# ── Word-level gap thresholds ─────────────────────────────────────────────────
# The "gap" (max_posterior - expected_phoneme_posterior) indicates error severity
GAP_THRESHOLD_MISPRONOUNCED = 2.0  # gap > 2.0 → likely mispronounced
GAP_THRESHOLD_UNCLEAR = 1.0  # gap 1.0-2.0 → unclear/borderline


def normalize_gop_score(raw_gop: float) -> float:
    """
    Map a single raw GOP log-probability to a 0-100 score.

    Args:
        raw_gop: Log-probability (negative, from the GOP engine)

    Returns:
        Score in [0.0, 100.0] where 100 = perfect pronunciation.
    """
    if raw_gop >= GOP_CEILING:
        return 100.0
    if raw_gop <= GOP_FLOOR:
        return 0.0

    # Linear interpolation between floor and ceiling
    normalized = (raw_gop - GOP_FLOOR) / (GOP_CEILING - GOP_FLOOR) * 100.0
    return round(max(0.0, min(100.0, normalized)), 1)


def normalize_word_scores(word_gop_results: list) -> list[dict]:
    """
    Convert a list of WordGOPResult objects into the frontend-compatible format
    with normalized 0-100 scores and issue classification.

    Args:
        word_gop_results: List of WordGOPResult from gop_engine.compute_gop_scores()

    Returns:
        List of dicts matching the existing ScoreResponse.word_scores format:
        [{word, word_score, detected_issue, expected_phonemes, substituted_as, confidence}]
    """
    results = []

    for word_result in word_gop_results:
        # Normalize the word-level GOP score to 0-100
        word_score = normalize_gop_score(word_result.word_gop_score)

        # Extract expected phonemes and identify substitutions
        expected_phonemes = [ps.phoneme for ps in word_result.phoneme_scores]
        substituted_as = []
        detected_issue = "correct"

        # Classify issue based on phoneme-level gaps
        max_gap = 0.0
        for ps in word_result.phoneme_scores:
            if ps.gap > max_gap:
                max_gap = ps.gap

            # If the model's best guess differs from expected AND the gap is large
            if ps.gap > GAP_THRESHOLD_MISPRONOUNCED:
                substituted_as.append(ps.max_posterior_phoneme)
            else:
                substituted_as.append(ps.phoneme)  # no substitution detected

        # Issue classification based on GOP scores
        if max_gap > GAP_THRESHOLD_MISPRONOUNCED:
            detected_issue = "mispronounced"
        elif max_gap > GAP_THRESHOLD_UNCLEAR:
            detected_issue = "unclear"
        elif word_score < 60.0:
            detected_issue = "unclear"

        results.append({
            "word": word_result.word,
            "word_score": round(word_score, 1),
            "detected_issue": detected_issue,
            "expected_phonemes": expected_phonemes,
            "substituted_as": substituted_as,
            "confidence": round(word_result.confidence, 3),
        })

    return results


def compute_overall_scores(normalized_word_scores: list[dict], words: list[dict], total_duration: float) -> dict:
    """
    Compute overall, accuracy, and fluency scores from normalized word results.

    Args:
        normalized_word_scores: Output from normalize_word_scores()
        words: Original word dicts with timestamps (for duration weighting)
        total_duration: Total recording duration in seconds

    Returns:
        {overall_score, accuracy_score, fluency_score, weak_phonemes}
    """
    from collections import Counter

    if not normalized_word_scores:
        return {
            "overall_score": 0.0,
            "accuracy_score": 0.0,
            "fluency_score": 0.0,
            "weak_phonemes": [],
        }

    # Overall: duration-weighted average of word scores
    total_weighted = 0.0
    total_weight = 0.0

    for ws, w in zip(normalized_word_scores, words):
        duration = max(w.get("end", 0) - w.get("start", 0), 0.01)
        total_weighted += ws["word_score"] * duration
        total_weight += duration

    overall_score = total_weighted / total_weight if total_weight > 0 else 0.0

    # Accuracy: mean word score (equally weighted)
    accuracy_score = np.mean([ws["word_score"] for ws in normalized_word_scores])

    # Fluency: based on speech rate and pauses (same logic as legacy)
    fluency_score = _compute_fluency(words, total_duration)

    # Weak phonemes: phonemes that appear in 2+ mispronounced words
    phoneme_issue_counter = Counter()
    for ws in normalized_word_scores:
        if ws["detected_issue"] == "mispronounced":
            for i, (exp, sub) in enumerate(
                zip(ws["expected_phonemes"], ws["substituted_as"])
            ):
                if exp != sub:
                    phoneme_issue_counter[exp] += 1

    weak_phonemes = [ph for ph, count in phoneme_issue_counter.items() if count >= 2]

    return {
        "overall_score": round(float(overall_score), 1),
        "accuracy_score": round(float(accuracy_score), 1),
        "fluency_score": round(float(fluency_score), 1),
        "weak_phonemes": weak_phonemes,
    }


def _compute_fluency(words: list[dict], total_duration: float) -> float:
    """
    Fluency sub-score (same methodology as legacy — this measures speech
    rate and pause patterns, which is orthogonal to pronunciation quality).
    """
    if not words or total_duration <= 0:
        return 0.0

    EXPECTED_WPM = 150.0

    # Speech rate
    word_count = len(words)
    speech_duration_min = total_duration / 60.0
    actual_wpm = word_count / speech_duration_min if speech_duration_min > 0 else 0

    rate_deviation = abs(actual_wpm - EXPECTED_WPM) / EXPECTED_WPM
    rate_penalty = min(rate_deviation * 30.0, 30.0)

    # Pause ratio
    speaking_time = sum(max(w.get("end", 0) - w.get("start", 0), 0) for w in words)
    silence_time = max(total_duration - speaking_time, 0)
    pause_ratio = silence_time / total_duration if total_duration > 0 else 0
    pause_penalty = min(pause_ratio * 50.0, 40.0)

    return max(100.0 - rate_penalty - pause_penalty, 0.0)
