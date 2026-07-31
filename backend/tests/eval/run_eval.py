#!/usr/bin/env python3
"""
Phase 26 — Scoring Evaluation Harness

Computes correlation between system pronunciation scores and human ratings.
Reports Pearson r, Spearman ρ, and Mean Absolute Error.

Usage:
    cd backend
    python tests/eval/run_eval.py [--engine gop|legacy]

Can also be run via pytest:
    pytest tests/eval/ -v
"""

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

GOLD_DATASET_DIR = Path(__file__).resolve().parent / "gold_dataset"
HUMAN_RATINGS_PATH = GOLD_DATASET_DIR / "human_ratings.csv"
RECORDINGS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "recordings"


def load_human_ratings() -> dict[str, float]:
    """Load human ratings from CSV. Returns {utterance_id: score}."""
    if not HUMAN_RATINGS_PATH.exists():
        raise FileNotFoundError(
            f"Human ratings not found at {HUMAN_RATINGS_PATH}. "
            "Run gold_dataset/generate_initial_ratings.py first."
        )

    ratings = {}
    with open(HUMAN_RATINGS_PATH) as f:
        reader = csv.DictReader(f)
        for row in reader:
            ratings[row["utterance_id"]] = float(row["score"])

    return ratings


def compute_system_scores(utterance_ids: list[str], engine: str = "gop") -> dict[str, float]:
    """
    Compute system pronunciation scores for the given utterance IDs.
    
    Args:
        utterance_ids: List of recording file stems (without .wav)
        engine: "gop" or "legacy"
    
    Returns:
        {utterance_id: system_score}
    """
    from app.modules.scoring.phoneme_recognizer import _ensure_model_loaded, load_audio_for_gop, get_frame_log_probs
    from app.modules.scoring.gop_engine import compute_gop_scores
    from app.modules.scoring.score_normalizer import normalize_word_scores, compute_overall_scores
    from app.modules.scoring.phoneme_compare import get_reference_phonemes
    from app.modules.scoring.legacy_diff_scorer import score_recording_legacy
    from app.modules.transcription.whisperx_client import transcribe_and_align

    if engine == "gop":
        _ensure_model_loaded()

    scores = {}
    for uid in utterance_ids:
        audio_path = RECORDINGS_DIR / f"{uid}.wav"
        if not audio_path.exists():
            continue

        try:
            # Transcribe
            transcript = transcribe_and_align(str(audio_path))
            words = transcript["words"]
            if not words:
                scores[uid] = 0.0
                continue

            total_duration = max(w["end"] for w in words)

            if engine == "legacy":
                result = score_recording_legacy(words, total_duration)
                scores[uid] = result["overall_score"]
            else:
                # GOP scoring
                audio_array, sr = load_audio_for_gop(str(audio_path))
                recognition = get_frame_log_probs(audio_array, sr)
                ref_phonemes = [get_reference_phonemes(w["word"]) for w in words]
                gop_results = compute_gop_scores(recognition, words, ref_phonemes)
                normalized = normalize_word_scores(gop_results)
                overall = compute_overall_scores(normalized, words, total_duration)
                scores[uid] = overall["overall_score"]

        except Exception as exc:
            print(f"  WARNING: Failed to score {uid}: {exc}")
            scores[uid] = 0.0

    return scores


def run_evaluation(engine: str = "gop", verbose: bool = True) -> dict:
    """
    Run the full evaluation: compute system scores and correlate with human ratings.
    
    Returns:
        {
            pearson_r: float,
            pearson_p: float,
            spearman_rho: float,
            spearman_p: float,
            mae: float,
            n_samples: int,
            engine: str,
            per_recording: [{utterance_id, human_score, system_score, error}],
        }
    """
    # Load human ratings
    human_ratings = load_human_ratings()
    utterance_ids = list(human_ratings.keys())

    if verbose:
        print(f"Evaluation: {len(utterance_ids)} recordings, engine={engine}")
        print(f"Computing system scores...")

    # Compute system scores
    system_scores = compute_system_scores(utterance_ids, engine=engine)

    # Align scores (only include utterances that have both)
    paired = []
    for uid in utterance_ids:
        if uid in system_scores:
            paired.append({
                "utterance_id": uid,
                "human_score": human_ratings[uid],
                "system_score": system_scores[uid],
                "error": system_scores[uid] - human_ratings[uid],
            })

    if len(paired) < 3:
        raise ValueError(f"Only {len(paired)} paired scores — need at least 3 for correlation")

    human_arr = np.array([p["human_score"] for p in paired])
    system_arr = np.array([p["system_score"] for p in paired])

    # Compute correlation metrics
    pearson_r, pearson_p = pearsonr(human_arr, system_arr)
    spearman_rho, spearman_p = spearmanr(human_arr, system_arr)
    mae = float(np.mean(np.abs(human_arr - system_arr)))

    result = {
        "pearson_r": round(float(pearson_r), 4),
        "pearson_p": round(float(pearson_p), 6),
        "spearman_rho": round(float(spearman_rho), 4),
        "spearman_p": round(float(spearman_p), 6),
        "mae": round(mae, 2),
        "n_samples": len(paired),
        "engine": engine,
        "human_mean": round(float(np.mean(human_arr)), 1),
        "human_std": round(float(np.std(human_arr)), 1),
        "system_mean": round(float(np.mean(system_arr)), 1),
        "system_std": round(float(np.std(system_arr)), 1),
        "per_recording": paired,
    }

    if verbose:
        print_report(result)

    return result


def print_report(result: dict):
    """Print a formatted evaluation report."""
    print(f"\n{'='*60}")
    print(f"SCORING EVALUATION REPORT — Engine: {result['engine']}")
    print(f"{'='*60}")
    print(f"  Samples:      {result['n_samples']}")
    print(f"  Pearson r:    {result['pearson_r']:.4f} (p={result['pearson_p']:.6f})")
    print(f"  Spearman ρ:   {result['spearman_rho']:.4f} (p={result['spearman_p']:.6f})")
    print(f"  MAE:          {result['mae']:.2f} points")
    print(f"  Human mean:   {result['human_mean']} (std={result['human_std']})")
    print(f"  System mean:  {result['system_mean']} (std={result['system_std']})")

    print(f"\n  Per-recording breakdown:")
    print(f"  {'ID':<36} {'Human':>6} {'System':>7} {'Error':>6}")
    print(f"  {'─'*58}")
    for p in result["per_recording"]:
        uid_short = p["utterance_id"][:12] + "..."
        print(f"  {uid_short:<36} {p['human_score']:>6.0f} {p['system_score']:>7.1f} {p['error']:>+6.1f}")

    # Interpretation
    r = result["pearson_r"]
    print(f"\n  Interpretation:")
    if r >= 0.8:
        print(f"  → Strong positive correlation (r={r:.2f}): system scores align well with human judgment")
    elif r >= 0.6:
        print(f"  → Moderate positive correlation (r={r:.2f}): reasonable agreement, room for calibration")
    elif r >= 0.4:
        print(f"  → Weak-moderate correlation (r={r:.2f}): some agreement but needs calibration work")
    else:
        print(f"  → Weak correlation (r={r:.2f}): scoring needs significant improvement")

    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Run scoring evaluation harness")
    parser.add_argument("--engine", choices=["gop", "legacy"], default="gop")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    result = run_evaluation(engine=args.engine, verbose=not args.quiet)
    return result


if __name__ == "__main__":
    main()
