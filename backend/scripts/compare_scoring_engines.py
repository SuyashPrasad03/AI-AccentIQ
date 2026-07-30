#!/usr/bin/env python3
"""
Phase 24 — Side-by-Side Scoring Engine Comparison Script

Runs both legacy (confidence-proxy) and GOP (acoustic) scoring engines on
real recordings stored in the local upload directory, and prints a detailed
comparison report.

Usage:
    cd backend
    python scripts/compare_scoring_engines.py [--recordings-dir PATH] [--limit N]

This script:
  1. Finds WAV files in the uploads directory
  2. Runs WhisperX/Deepgram transcription (or uses existing transcript from Mongo)
  3. Runs both scoring engines
  4. Prints a side-by-side comparison table
  5. Confirms model is loaded once (warm)
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

# Add the backend root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np


def find_recordings(recordings_dir: Path, limit: int) -> list[Path]:
    """Find WAV files in the recordings directory."""
    patterns = ["**/*.wav", "**/*.WAV", "**/*.mp3", "**/*.flac"]
    files = []
    for pattern in patterns:
        files.extend(recordings_dir.glob(pattern))
    files.sort()
    return files[:limit]


def run_comparison(audio_path: Path) -> dict:
    """
    Run both scoring engines on a single audio file.
    Returns a comparison dict.
    """
    from app.modules.scoring.phoneme_recognizer import (
        get_frame_log_probs,
        load_audio_for_gop,
        is_model_loaded,
    )
    from app.modules.scoring.gop_engine import compute_gop_scores
    from app.modules.scoring.score_normalizer import (
        normalize_word_scores,
        compute_overall_scores,
    )
    from app.modules.scoring.phoneme_compare import get_reference_phonemes
    from app.modules.scoring.legacy_diff_scorer import score_recording_legacy
    from app.modules.transcription.whisperx_client import transcribe_and_align

    # Step 1: Transcribe the audio
    print(f"  Transcribing: {audio_path.name}...")
    transcript = transcribe_and_align(str(audio_path))
    words = transcript["words"]
    total_duration = max((w["end"] for w in words), default=10.0) if words else 10.0

    if not words:
        return {"error": "No words transcribed", "file": audio_path.name}

    # Step 2: Run legacy scoring
    legacy_start = time.time()
    legacy_result = score_recording_legacy(words, total_duration)
    legacy_time = time.time() - legacy_start

    # Step 3: Run GOP scoring
    gop_start = time.time()
    audio_array, sample_rate = load_audio_for_gop(str(audio_path))
    recognition = get_frame_log_probs(audio_array, sample_rate)

    ref_phonemes = [get_reference_phonemes(w["word"]) for w in words]
    gop_results = compute_gop_scores(recognition, words, ref_phonemes)
    normalized = normalize_word_scores(gop_results)
    overall = compute_overall_scores(normalized, words, total_duration)
    gop_time = time.time() - gop_start

    return {
        "file": audio_path.name,
        "word_count": len(words),
        "transcript": transcript["raw_text"][:80],
        "model_version": transcript["model_version"],
        "legacy": {
            "overall": legacy_result["overall_score"],
            "accuracy": legacy_result["accuracy_score"],
            "fluency": legacy_result["fluency_score"],
            "word_scores": [(ws["word"], ws["word_score"], ws["detected_issue"])
                           for ws in legacy_result["word_scores"][:10]],
            "weak_phonemes": legacy_result["weak_phonemes"],
            "time_ms": round(legacy_time * 1000, 1),
        },
        "gop": {
            "overall": overall["overall_score"],
            "accuracy": overall["accuracy_score"],
            "fluency": overall["fluency_score"],
            "word_scores": [(ws["word"], ws["word_score"], ws["detected_issue"])
                           for ws in normalized[:10]],
            "weak_phonemes": overall["weak_phonemes"],
            "time_ms": round(gop_time * 1000, 1),
        },
        "model_warm": is_model_loaded(),
    }


def print_report(comparisons: list[dict]):
    """Print a formatted comparison report."""
    print("\n" + "=" * 80)
    print("PHASE 24 — SCORING ENGINE COMPARISON REPORT")
    print("Legacy (confidence-proxy) vs. GOP (acoustic wav2vec2-CTC)")
    print("=" * 80)

    for i, comp in enumerate(comparisons, 1):
        if "error" in comp:
            print(f"\n[{i}] {comp['file']} — ERROR: {comp['error']}")
            continue

        print(f"\n{'─' * 80}")
        print(f"[{i}] {comp['file']}")
        print(f"    Transcript: \"{comp['transcript']}...\"")
        print(f"    Words: {comp['word_count']}  |  ASR: {comp['model_version']}")
        print(f"    Model warm: {'✓' if comp['model_warm'] else '✗'}")
        print()

        # Overall scores
        l = comp["legacy"]
        g = comp["gop"]
        print(f"    {'METRIC':<15} {'LEGACY':>8} {'GOP':>8} {'DELTA':>8}")
        print(f"    {'─' * 45}")
        print(f"    {'Overall':<15} {l['overall']:>8.1f} {g['overall']:>8.1f} {g['overall']-l['overall']:>+8.1f}")
        print(f"    {'Accuracy':<15} {l['accuracy']:>8.1f} {g['accuracy']:>8.1f} {g['accuracy']-l['accuracy']:>+8.1f}")
        print(f"    {'Fluency':<15} {l['fluency']:>8.1f} {g['fluency']:>8.1f} {g['fluency']-l['fluency']:>+8.1f}")
        print(f"    {'Time (ms)':<15} {l['time_ms']:>8.1f} {g['time_ms']:>8.1f}")

        # Per-word scores (first 5)
        print(f"\n    {'WORD':<12} {'L-SCORE':>8} {'L-ISSUE':<14} {'G-SCORE':>8} {'G-ISSUE':<14}")
        print(f"    {'─' * 60}")
        max_words = min(5, len(l["word_scores"]), len(g["word_scores"]))
        for j in range(max_words):
            lw = l["word_scores"][j]
            gw = g["word_scores"][j]
            print(f"    {lw[0]:<12} {lw[1]:>8.1f} {lw[2]:<14} {gw[1]:>8.1f} {gw[2]:<14}")

        # Weak phonemes
        if l["weak_phonemes"] or g["weak_phonemes"]:
            print(f"\n    Weak phonemes (legacy): {l['weak_phonemes']}")
            print(f"    Weak phonemes (GOP):    {g['weak_phonemes']}")

    # Summary statistics
    valid = [c for c in comparisons if "error" not in c]
    if valid:
        print(f"\n{'=' * 80}")
        print("SUMMARY")
        print(f"{'=' * 80}")
        legacy_overalls = [c["legacy"]["overall"] for c in valid]
        gop_overalls = [c["gop"]["overall"] for c in valid]
        deltas = [g - l for g, l in zip(gop_overalls, legacy_overalls)]

        print(f"  Recordings analyzed: {len(valid)}")
        print(f"  Legacy overall mean: {np.mean(legacy_overalls):.1f} (std={np.std(legacy_overalls):.1f})")
        print(f"  GOP overall mean:    {np.mean(gop_overalls):.1f} (std={np.std(gop_overalls):.1f})")
        print(f"  Mean delta (GOP-Legacy): {np.mean(deltas):+.1f}")
        print(f"  Legacy score range: [{min(legacy_overalls):.1f}, {max(legacy_overalls):.1f}]")
        print(f"  GOP score range:    [{min(gop_overalls):.1f}, {max(gop_overalls):.1f}]")

        # GOP differentiation
        print(f"\n  GOP standard deviation of overall scores: {np.std(gop_overalls):.2f}")
        print(f"  Legacy standard deviation of overall scores: {np.std(legacy_overalls):.2f}")
        if np.std(gop_overalls) > np.std(legacy_overalls):
            print("  → GOP produces MORE differentiated scores ✓")
        else:
            print("  → GOP produces less differentiated scores (may need calibration refinement)")

        # Model warm check
        all_warm = all(c.get("model_warm", False) for c in valid)
        print(f"\n  Model stayed warm across all recordings: {'✓' if all_warm else '✗'}")

    print(f"\n{'=' * 80}\n")


def main():
    parser = argparse.ArgumentParser(description="Compare legacy vs GOP scoring engines")
    parser.add_argument(
        "--recordings-dir",
        type=Path,
        default=None,
        help="Directory containing audio recordings (default: ./uploads)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of recordings to process (default: 5)",
    )
    args = parser.parse_args()

    # Determine recordings directory
    if args.recordings_dir:
        recordings_dir = args.recordings_dir
    else:
        # Try common locations
        candidates = [
            Path("./uploads"),
            Path("../uploads"),
            Path("/app/storage"),
        ]
        recordings_dir = None
        for c in candidates:
            if c.exists():
                recordings_dir = c
                break

        if recordings_dir is None:
            print("ERROR: No recordings directory found.")
            print("Specify with --recordings-dir or place WAV files in ./uploads/")
            sys.exit(1)

    print(f"Looking for recordings in: {recordings_dir.resolve()}")
    recordings = find_recordings(recordings_dir, args.limit)

    if not recordings:
        print(f"No audio files found in {recordings_dir}")
        print("Place WAV/MP3/FLAC files there to run the comparison.")
        sys.exit(1)

    print(f"Found {len(recordings)} recording(s)")

    # Pre-load the model (confirm it loads once)
    print("\nPre-loading wav2vec2-CTC model (one-time)...")
    load_start = time.time()
    from app.modules.scoring.phoneme_recognizer import _ensure_model_loaded, is_model_loaded
    _ensure_model_loaded()
    load_time = time.time() - load_start
    print(f"  Model loaded in {load_time:.1f}s — warm: {is_model_loaded()}")

    # Run comparisons
    comparisons = []
    for audio_path in recordings:
        try:
            result = run_comparison(audio_path)
            comparisons.append(result)
        except Exception as exc:
            print(f"  ERROR on {audio_path.name}: {exc}")
            comparisons.append({"error": str(exc), "file": audio_path.name})

    # Print report
    print_report(comparisons)


if __name__ == "__main__":
    main()
