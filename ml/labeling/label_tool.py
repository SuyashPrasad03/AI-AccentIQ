#!/usr/bin/env python3
"""
Phase 25 — Pronunciation Error Labeling Tool

Generates labeled training data for the error-type classifier using a
hybrid weak-supervision + rule-based approach:

1. Runs the GOP engine on all available recordings
2. Applies rule-based heuristics to assign initial error-type labels:
   - GOP gap > 3.0 → substitution (model confidently predicts a different phoneme)
   - GOP gap > 2.0 AND duration_ratio < 0.3 → deletion (phoneme too short)
   - GOP gap > 2.0 AND duration_ratio > 2.0 → insertion (extra time, likely added phoneme)
   - GOP gap 1.0-3.0 AND low energy → distortion (phoneme attempted but malformed)
   - GOP gap < 1.0 → correct
3. Exports as labeled_dataset.csv for training

LABELING METHODOLOGY (documented for interview/audit):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Source: 18 real user recordings from AccentIQ production (with consent).
Initial labels: Rule-based from GOP gap magnitude, duration ratio, and energy.
Validation: Manual review of a sample to confirm rule quality.

The rule-based approach is a legitimate weak-supervision methodology (Ratner et al.,
"Data Programming", NeurIPS 2016) — we define labeling functions that produce noisy
labels, then train a model that generalizes beyond the rules.

Error type definitions:
  - correct: Phoneme matches expected, GOP gap < 1.0
  - substitution: Different phoneme produced (e.g., /θ/ → /t/), GOP gap > 3.0
  - deletion: Phoneme omitted or severely shortened, duration_ratio < 0.3
  - insertion: Extra phoneme added, unusually long segment for context
  - distortion: Phoneme attempted but acoustically poor, moderate gap + low energy

Usage:
    cd backend
    python ../ml/labeling/label_tool.py --recordings-dir uploads/recordings --output ../ml/labeling/labeled_dataset.csv
"""

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))


def label_from_gop_features(
    gop_score: float,
    gop_gap: float,
    duration: float,
    duration_ratio: float,
    energy_mean: float,
    phoneme: str,
    max_posterior_phoneme: str,
) -> tuple[str, float]:
    """
    Rule-based labeling function.

    Returns (error_type, confidence) tuple.
    """
    # Strong substitution: model very confidently predicts a different phoneme
    if gop_gap > 3.0 and phoneme != max_posterior_phoneme:
        return "substitution", min(0.95, 0.5 + gop_gap * 0.1)

    # Deletion: phoneme segment is extremely short
    if duration_ratio < 0.3 and gop_gap > 1.5:
        return "deletion", min(0.90, 0.5 + (1.0 - duration_ratio) * 0.4)

    # Insertion: unusually long segment (more than 2x expected)
    if duration_ratio > 2.5 and gop_gap > 1.5:
        return "insertion", min(0.80, 0.5 + (duration_ratio - 2.0) * 0.15)

    # Distortion: moderate gap + low energy (phoneme attempted but poorly)
    if 1.5 < gop_gap <= 3.0 and energy_mean < 0.02:
        return "distortion", min(0.75, 0.4 + gop_gap * 0.1)

    # Moderate gap, moderate energy → likely distortion
    if 2.0 < gop_gap <= 3.0:
        return "distortion", min(0.70, 0.3 + gop_gap * 0.1)

    # Correct: low gap, phoneme matches well
    if gop_gap < 1.0:
        return "correct", min(0.95, 0.7 + (1.0 - gop_gap) * 0.25)

    # Borderline: moderate gap, classify as distortion with lower confidence
    if 1.0 <= gop_gap <= 2.0:
        return "distortion", 0.55

    return "correct", 0.50


def process_recording(audio_path: Path) -> list[dict]:
    """Process a single recording and return labeled phoneme samples."""
    from app.modules.scoring.phoneme_recognizer import (
        get_frame_log_probs,
        load_audio_for_gop,
    )
    from app.modules.scoring.gop_engine import compute_gop_scores
    from app.modules.scoring.phoneme_compare import get_reference_phonemes
    from app.modules.scoring.error_classifier.feature_extraction import (
        extract_phoneme_features,
        _EXPECTED_DURATIONS,
        DEFAULT_EXPECTED_DURATION,
    )
    from app.modules.transcription.whisperx_client import transcribe_and_align

    # Transcribe
    transcript = transcribe_and_align(str(audio_path))
    words = transcript["words"]
    if not words:
        return []

    # Load audio for GOP
    audio_array, sr = load_audio_for_gop(str(audio_path))

    # Get frame-level log-probs
    recognition = get_frame_log_probs(audio_array, sr)

    # Get reference phonemes
    ref_phonemes = [get_reference_phonemes(w["word"]) for w in words]

    # Compute GOP
    gop_results = compute_gop_scores(recognition, words, ref_phonemes)

    # Extract labeled samples
    samples = []
    for word_result in gop_results:
        word_duration = word_result.end - word_result.start
        if word_duration <= 0 or not word_result.phoneme_scores:
            continue

        num_phonemes = len(word_result.phoneme_scores)
        time_per_phoneme = word_duration / num_phonemes

        for ph_idx, ps in enumerate(word_result.phoneme_scores):
            ph_start = word_result.start + ph_idx * time_per_phoneme
            ph_end = ph_start + time_per_phoneme

            # Duration ratio
            expected_dur = _EXPECTED_DURATIONS.get(ps.phoneme, DEFAULT_EXPECTED_DURATION)
            duration_ratio = time_per_phoneme / expected_dur if expected_dur > 0 else 1.0

            # Extract energy for this segment
            start_sample = int(ph_start * sr)
            end_sample = int(ph_end * sr)
            start_sample = max(0, min(start_sample, len(audio_array) - 1))
            end_sample = max(start_sample + 1, min(end_sample, len(audio_array)))
            segment = audio_array[start_sample:end_sample]
            energy_mean = float(np.sqrt(np.mean(segment ** 2))) if len(segment) > 0 else 0.0

            # Apply labeling rules
            error_type, confidence = label_from_gop_features(
                gop_score=ps.gop_score,
                gop_gap=ps.gap,
                duration=time_per_phoneme,
                duration_ratio=duration_ratio,
                energy_mean=energy_mean,
                phoneme=ps.phoneme,
                max_posterior_phoneme=ps.max_posterior_phoneme,
            )

            samples.append({
                "recording_file": audio_path.name,
                "word": word_result.word,
                "phoneme": ps.phoneme,
                "phoneme_index": ph_idx,
                "start_time": round(ph_start, 4),
                "end_time": round(ph_end, 4),
                "duration": round(time_per_phoneme, 4),
                "duration_ratio": round(duration_ratio, 3),
                "gop_score": ps.gop_score,
                "gop_gap": ps.gap,
                "max_posterior_phoneme": ps.max_posterior_phoneme,
                "energy_mean": round(energy_mean, 6),
                "error_type": error_type,
                "label_confidence": round(confidence, 3),
                "label_source": "rule_based_v1",
            })

    return samples


def main():
    parser = argparse.ArgumentParser(description="Generate labeled dataset for error classifier")
    parser.add_argument(
        "--recordings-dir", type=Path,
        default=Path("uploads/recordings"),
        help="Directory containing audio recordings",
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("../ml/labeling/labeled_dataset.csv"),
        help="Output CSV path",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max recordings to process")
    args = parser.parse_args()

    recordings = sorted(args.recordings_dir.glob("*.wav"))
    if args.limit:
        recordings = recordings[:args.limit]

    print(f"Processing {len(recordings)} recordings...")

    # Pre-load model
    from app.modules.scoring.phoneme_recognizer import _ensure_model_loaded
    print("Loading wav2vec2-CTC model...")
    _ensure_model_loaded()
    print("Model loaded.")

    all_samples = []
    for i, rec_path in enumerate(recordings):
        print(f"  [{i+1}/{len(recordings)}] {rec_path.name}...")
        try:
            samples = process_recording(rec_path)
            all_samples.extend(samples)
            print(f"    → {len(samples)} phoneme samples extracted")
        except Exception as exc:
            print(f"    → ERROR: {exc}")

    # Write CSV
    if not all_samples:
        print("No samples extracted!")
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(all_samples[0].keys())
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_samples)

    # Summary
    from collections import Counter
    type_counts = Counter(s["error_type"] for s in all_samples)

    print(f"\n{'='*60}")
    print(f"LABELED DATASET GENERATED")
    print(f"{'='*60}")
    print(f"  Total phoneme samples: {len(all_samples)}")
    print(f"  Output: {args.output}")
    print(f"\n  Error type distribution:")
    for etype, count in sorted(type_counts.items()):
        pct = count / len(all_samples) * 100
        print(f"    {etype:<14} {count:>5} ({pct:.1f}%)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
