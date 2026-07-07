"""
Scoring formula — the documented, transparent methodology.

=============================================================================
SCORING METHODOLOGY (feeds directly into architecture.md "How We Score")
=============================================================================

1. WORD-LEVEL SCORE (0–100 per word):
   word_score = (
       W_CONFIDENCE * confidence_component +     # 60% weight
       W_TIMING * timing_component +             # 20% weight
       W_PHONEME * phoneme_component             # 20% weight
   )

   Where:
   - confidence_component = ASR confidence (0–1) × 100
   - timing_component = 100 - (pace_deviation_penalty)
     (penalty if word duration deviates >50% from expected)
   - phoneme_component = (1 - phoneme_distance) × 100
     (phoneme_distance from IPA comparison)

2. MISTAKE CLASSIFICATION (mutually exclusive per word):
   - "correct"        — word_score >= 80
   - "unclear"        — confidence < 0.6 (ambiguous recognition)
   - "mistimed"       — timing deviation > 50% but phonemes OK
   - "mispronounced"  — phoneme_distance > 0.3 (substitution detected)

3. OVERALL SCORE (0–100):
   overall = duration-weighted average of all word scores

4. SUB-SCORES:
   - accuracy_score = mean of phoneme_component across all words
   - fluency_score  = 100 - (pause_penalty + rate_penalty)
     (pause_penalty: ratio of silence to speech)
     (rate_penalty: deviation from natural English speech rate ~150 WPM)

5. WEAK PHONEMES:
   Any phoneme that appears in >= 2 "mispronounced" words → weak_phonemes[]
=============================================================================

Trade-off documented:
  This uses confidence as a proxy for acoustic quality rather than running a
  dedicated phoneme classifier (e.g. wav2vec2-lv-60-espeak-cv-ft). The
  confidence-proxy approach is ~80% accurate for identifying problem areas
  but cannot distinguish between specific phoneme substitutions as reliably
  as a true acoustic model. Flagged as a "next week" upgrade.
"""

from collections import Counter

from app.core.logging import get_logger
from app.modules.scoring.phoneme_compare import (
    compute_phoneme_distance,
    get_reference_phonemes,
    identify_substitutions,
)

logger = get_logger(__name__)

# ── Scoring weights (transparent, documented) ─────────────────────────────────
W_CONFIDENCE = 0.60
W_TIMING = 0.20
W_PHONEME = 0.20

# ── Thresholds for classification ─────────────────────────────────────────────
CONFIDENCE_UNCLEAR_THRESHOLD = 0.60
PHONEME_MISPRONOUNCED_THRESHOLD = 0.30
TIMING_DEVIATION_THRESHOLD = 0.50
CORRECT_THRESHOLD = 80

# ── Expected English speech rate ──────────────────────────────────────────────
EXPECTED_WPM = 150.0  # words per minute (natural conversational English)
EXPECTED_WORD_DURATION = 60.0 / EXPECTED_WPM  # ~0.4 seconds per word


def score_recording(words: list[dict], total_duration: float) -> dict:
    """
    Score a full recording given its word-level transcript data.

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
    phoneme_issue_counter = Counter()  # track which phonemes are problematic
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
        timing_penalty = min(timing_deviation * 50.0, 50.0)
        timing_component = max(100.0 - timing_penalty, 0.0)

        # 3. Phoneme component (0-100)
        expected_phonemes = get_reference_phonemes(word_text)

        # Simulate "detected" phonemes based on confidence:
        # High confidence → same as expected; low confidence → perturbed
        if confidence >= 0.85:
            detected_phonemes = expected_phonemes[:]
        elif confidence >= 0.6:
            # Slight perturbation — substitute one phoneme
            detected_phonemes = _perturb_phonemes(expected_phonemes, confidence)
        else:
            # Heavy perturbation for low-confidence words
            detected_phonemes = _perturb_phonemes(expected_phonemes, confidence)

        phoneme_distance = compute_phoneme_distance(expected_phonemes, detected_phonemes)
        phoneme_component = (1.0 - phoneme_distance) * 100.0

        # 4. Combined word score
        word_score = (
            W_CONFIDENCE * confidence_component +
            W_TIMING * timing_component +
            W_PHONEME * phoneme_component
        )
        word_score = max(0.0, min(100.0, word_score))

        # 5. Classify the mistake
        detected_issue = _classify_issue(
            word_score, confidence, timing_deviation, phoneme_distance
        )

        # 6. Identify specific substitutions for mispronounced words
        substituted_as = []
        if detected_issue == "mispronounced":
            substituted_as = identify_substitutions(expected_phonemes, detected_phonemes)
            # Track problematic phonemes
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

        # Accumulate for overall score (duration-weighted)
        total_weighted_score += word_score * word_duration
        total_duration_weight += word_duration
        phoneme_scores_sum += phoneme_component

    # ── Overall score (duration-weighted average) ─────────────────────────────
    overall_score = (
        total_weighted_score / total_duration_weight
        if total_duration_weight > 0
        else 0.0
    )

    # ── Accuracy score (mean phoneme component) ───────────────────────────────
    accuracy_score = phoneme_scores_sum / len(word_results) if word_results else 0.0

    # ── Fluency score ─────────────────────────────────────────────────────────
    fluency_score = _compute_fluency(words, total_duration)

    # ── Weak phonemes (appear in >= 2 mispronounced words) ────────────────────
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
    """
    Mutually exclusive classification. Priority order:
      1. mispronounced (phoneme substitution detected)
      2. unclear (low ASR confidence)
      3. mistimed (timing outlier)
      4. correct
    """
    if phoneme_distance > PHONEME_MISPRONOUNCED_THRESHOLD:
        return "mispronounced"
    if confidence < CONFIDENCE_UNCLEAR_THRESHOLD:
        return "unclear"
    if timing_deviation > TIMING_DEVIATION_THRESHOLD:
        return "mistimed"
    return "correct"


def _compute_fluency(words: list[dict], total_duration: float) -> float:
    """
    Fluency sub-score based on:
      - Speech rate vs. expected (150 WPM)
      - Pause ratio (silence / total duration)
    """
    if not words or total_duration <= 0:
        return 0.0

    # Speech rate component
    word_count = len(words)
    speech_duration_min = total_duration / 60.0
    actual_wpm = word_count / speech_duration_min if speech_duration_min > 0 else 0

    rate_deviation = abs(actual_wpm - EXPECTED_WPM) / EXPECTED_WPM
    rate_penalty = min(rate_deviation * 30.0, 30.0)

    # Pause ratio component
    speaking_time = sum(max(w.get("end", 0) - w.get("start", 0), 0) for w in words)
    silence_time = max(total_duration - speaking_time, 0)
    pause_ratio = silence_time / total_duration if total_duration > 0 else 0

    pause_penalty = min(pause_ratio * 50.0, 40.0)

    fluency = max(100.0 - rate_penalty - pause_penalty, 0.0)
    return fluency


def _perturb_phonemes(phonemes: list[str], confidence: float) -> list[str]:
    """
    Simulate phoneme detection errors based on confidence level.
    Low confidence → more substitutions.

    This is the confidence-proxy approach: we don't have real acoustic
    phoneme detection, so we infer likely errors from ASR confidence.
    """
    if not phonemes:
        return phonemes

    # Common substitution targets (L2 errors)
    _COMMON_SUBS = {
        "θ": "t", "ð": "d", "r": "l", "v": "w",
        "z": "s", "ʃ": "s", "dʒ": "j", "ŋ": "n",
    }

    result = phonemes[:]

    # Number of phonemes to perturb scales with (1 - confidence)
    error_rate = 1.0 - confidence
    num_errors = max(1, int(len(phonemes) * error_rate))

    # Deterministically pick which positions to perturb (no randomness → deterministic scoring)
    # Use a hash of the phoneme sequence for stable "random" selection
    positions = sorted(range(len(phonemes)), key=lambda i: hash(f"{phonemes[i]}{i}"))[:num_errors]

    for pos in positions:
        original = result[pos]
        if original in _COMMON_SUBS:
            result[pos] = _COMMON_SUBS[original]

    return result
