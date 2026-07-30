"""
Legacy scoring engine — confidence-proxy + phoneme string-diff approach.

=============================================================================
KEPT AS FALLBACK / COMPARISON MODE (Phase 24 refactor)
=============================================================================

This is the original scoring methodology (Phases 1–23). It uses ASR confidence
as a proxy for acoustic quality and computes a weighted Levenshtein distance
between reference phonemes and "detected" phonemes (which are actually derived
from the confidence value, not from acoustic recognition).

Known limitations (documented in the upgrade phase pack):
  1. "Detected" phonemes are fabricated from confidence, not actually recognized.
  2. No acoustic grounding — scores reflect ASR confidence, not pronunciation quality.
  3. No calibration — arbitrary formula with hand-picked weights.
  4. No L1/accent baseline — same reference for all users.

This module is retained for:
  - A/B comparison logging during the transition to GOP scoring.
  - Fallback if the GOP model fails to load or process.
  - Benchmarking (Phase 26) to prove GOP is actually better.

Original docstring preserved below:
─────────────────────────────────────────────────────────────────────────────

Scoring formula — the documented, transparent methodology.

1. WORD-LEVEL SCORE (0–100 per word):
   word_score = (
       W_CONFIDENCE * confidence_component +     # 35% weight
       W_TIMING * timing_component +             # 30% weight
       W_PHONEME * phoneme_component             # 35% weight
   )

2. MISTAKE CLASSIFICATION (mutually exclusive per word):
   - "correct"        — word_score >= 80
   - "unclear"        — confidence < 0.6
   - "mistimed"       — timing deviation > 50% but phonemes OK
   - "mispronounced"  — phoneme_distance > 0.3

3. OVERALL SCORE (0–100):
   overall = duration-weighted average of all word scores

4. SUB-SCORES:
   - accuracy_score = mean of phoneme_component across all words
   - fluency_score  = 100 - (pause_penalty + rate_penalty)
"""

from collections import Counter

from app.core.logging import get_logger
from app.modules.scoring.phoneme_compare import (
    compute_phoneme_distance,
    get_reference_phonemes,
    identify_substitutions,
)

logger = get_logger(__name__)

# ── Scoring weights ───────────────────────────────────────────────────────────
W_CONFIDENCE = 0.35
W_TIMING = 0.30
W_PHONEME = 0.35

# ── Thresholds ────────────────────────────────────────────────────────────────
CONFIDENCE_UNCLEAR_THRESHOLD = 0.60
PHONEME_MISPRONOUNCED_THRESHOLD = 0.30
TIMING_DEVIATION_THRESHOLD = 0.50
CORRECT_THRESHOLD = 80

# ── Expected English speech rate ──────────────────────────────────────────────
EXPECTED_WPM = 150.0
EXPECTED_WORD_DURATION = 60.0 / EXPECTED_WPM  # ~0.4 seconds per word


def score_recording_legacy(words: list[dict], total_duration: float) -> dict:
    """
    Legacy scoring: score a full recording using the confidence-proxy approach.

    Args:
        words: list of {word, start, end, confidence} from WhisperX
        total_duration: total recording duration in seconds

    Returns:
        {
            overall_score: float (0-100),
            accuracy_score: float (0-100),
            fluency_score: float (0-100),
            word_scores: [{word, word_score, detected_issue, expected_phonemes,
                          substituted_as, confidence}],
            weak_phonemes: [str]
        }
    """
    if not words:
        return {
            "overall_score": 0.0,
            "accuracy_score": 0.0,
            "fluency_score": 0.0,
            "word_scores": [],
            "weak_phonemes": [],
        }

    word_results = []
    phoneme_issue_counter = Counter()
    total_weighted_score = 0.0
    total_duration_weight = 0.0
    phoneme_scores_sum = 0.0

    for w in words:
        word_text = w.get("word", "").strip()
        confidence = w.get("confidence", 0.0)
        start = w.get("start", 0.0)
        end = w.get("end", 0.0)
        word_duration = max(end - start, 0.01)

        if not word_text:
            continue

        # 1. Confidence component (0-100)
        confidence_component = confidence * 100.0

        # 2. Timing component (0-100)
        timing_deviation = abs(word_duration - EXPECTED_WORD_DURATION) / EXPECTED_WORD_DURATION
        timing_penalty = min(timing_deviation * 80.0, 70.0)
        timing_component = max(100.0 - timing_penalty, 0.0)

        # 3. Phoneme component (0-100) — confidence-proxy approach
        expected_phonemes = get_reference_phonemes(word_text)

        if confidence >= 0.95:
            detected_phonemes = expected_phonemes[:]
        elif confidence >= 0.80:
            detected_phonemes = _perturb_phonemes(expected_phonemes, confidence * 0.9)
        elif confidence >= 0.6:
            detected_phonemes = _perturb_phonemes(expected_phonemes, confidence * 0.8)
        else:
            detected_phonemes = _perturb_phonemes(expected_phonemes, confidence * 0.7)

        phoneme_distance = compute_phoneme_distance(expected_phonemes, detected_phonemes)
        phoneme_component = (1.0 - phoneme_distance) * 100.0

        # 4. Combined word score
        word_score = (
            W_CONFIDENCE * confidence_component +
            W_TIMING * timing_component +
            W_PHONEME * phoneme_component
        )
        word_score = max(0.0, min(100.0, word_score))

        # 5. Classify
        detected_issue = _classify_issue(
            word_score, confidence, timing_deviation, phoneme_distance
        )

        # 6. Identify substitutions
        substituted_as = []
        if detected_issue == "mispronounced":
            substituted_as = identify_substitutions(expected_phonemes, detected_phonemes)
            for exp, det in zip(expected_phonemes, substituted_as):
                if exp != det and det != "∅":
                    phoneme_issue_counter[exp] += 1

        word_results.append({
            "word": word_text,
            "word_score": round(word_score, 1),
            "detected_issue": detected_issue,
            "expected_phonemes": expected_phonemes,
            "substituted_as": substituted_as,
            "confidence": round(confidence, 3),
        })

        total_weighted_score += word_score * word_duration
        total_duration_weight += word_duration
        phoneme_scores_sum += phoneme_component

    # Overall score (duration-weighted)
    overall_score = (
        total_weighted_score / total_duration_weight
        if total_duration_weight > 0
        else 0.0
    )

    # Accuracy (mean phoneme component)
    accuracy_score = phoneme_scores_sum / len(word_results) if word_results else 0.0

    # Fluency
    fluency_score = _compute_fluency(words, total_duration)

    # Weak phonemes
    weak_phonemes = [ph for ph, count in phoneme_issue_counter.items() if count >= 2]

    return {
        "overall_score": round(overall_score, 1),
        "accuracy_score": round(accuracy_score, 1),
        "fluency_score": round(fluency_score, 1),
        "word_scores": word_results,
        "weak_phonemes": weak_phonemes,
    }


def _classify_issue(
    word_score: float,
    confidence: float,
    timing_deviation: float,
    phoneme_distance: float,
) -> str:
    if phoneme_distance > PHONEME_MISPRONOUNCED_THRESHOLD:
        return "mispronounced"
    if confidence < CONFIDENCE_UNCLEAR_THRESHOLD:
        return "unclear"
    if timing_deviation > TIMING_DEVIATION_THRESHOLD:
        return "mistimed"
    return "correct"


def _compute_fluency(words: list[dict], total_duration: float) -> float:
    if not words or total_duration <= 0:
        return 0.0

    word_count = len(words)
    speech_duration_min = total_duration / 60.0
    actual_wpm = word_count / speech_duration_min if speech_duration_min > 0 else 0

    rate_deviation = abs(actual_wpm - EXPECTED_WPM) / EXPECTED_WPM
    rate_penalty = min(rate_deviation * 30.0, 30.0)

    speaking_time = sum(max(w.get("end", 0) - w.get("start", 0), 0) for w in words)
    silence_time = max(total_duration - speaking_time, 0)
    pause_ratio = silence_time / total_duration if total_duration > 0 else 0
    pause_penalty = min(pause_ratio * 50.0, 40.0)

    return max(100.0 - rate_penalty - pause_penalty, 0.0)


def _perturb_phonemes(phonemes: list[str], confidence: float) -> list[str]:
    """
    Simulate phoneme detection errors based on confidence level.
    Low confidence → more substitutions.
    """
    if not phonemes:
        return phonemes

    _COMMON_SUBS = {
        "θ": "t", "ð": "d", "r": "l", "v": "w",
        "z": "s", "ʃ": "s", "dʒ": "j", "ŋ": "n",
    }

    result = phonemes[:]
    error_rate = 1.0 - confidence
    num_errors = max(1, int(len(phonemes) * error_rate))

    positions = sorted(range(len(phonemes)), key=lambda i: hash(f"{phonemes[i]}{i}"))[:num_errors]

    for pos in positions:
        original = result[pos]
        if original in _COMMON_SUBS:
            result[pos] = _COMMON_SUBS[original]

    return result
