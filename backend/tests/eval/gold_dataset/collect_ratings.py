#!/usr/bin/env python3
"""
Phase 26 — Human Rating Collection Tool

Plays each recording and prompts the rater to assign a pronunciation score (0-100).
Outputs human_ratings.csv for use in the evaluation harness.

Rating criteria (given to all raters):
  100: Native-like pronunciation, natural rhythm, no detectable errors
  80-99: Very good, minor issues that don't affect intelligibility
  60-79: Good, some noticeable errors but clearly intelligible
  40-59: Fair, several errors that occasionally affect understanding
  20-39: Poor, frequent errors that significantly impair understanding
  0-19: Very poor, largely unintelligible

Usage:
    cd backend
    python tests/eval/gold_dataset/collect_ratings.py --recordings-dir uploads/recordings

Note: This tool requires a terminal that can play audio. On macOS, uses `afplay`.
If unavailable, the rater listens to the file externally and enters the score.
"""

import argparse
import csv
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def play_audio(path: Path) -> bool:
    """Try to play the audio file. Returns True if playback started."""
    try:
        # macOS
        subprocess.Popen(
            ["afplay", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except FileNotFoundError:
        pass

    try:
        # Linux
        subprocess.Popen(
            ["aplay", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except FileNotFoundError:
        pass

    return False


def collect_ratings(recordings_dir: Path, output_path: Path, rater_id: str):
    """Interactively collect human ratings for each recording."""
    recordings = sorted(recordings_dir.glob("*.wav"))

    if not recordings:
        print(f"No recordings found in {recordings_dir}")
        return

    print(f"\n{'='*60}")
    print("PRONUNCIATION RATING TASK")
    print(f"{'='*60}")
    print(f"Rater: {rater_id}")
    print(f"Recordings: {len(recordings)}")
    print(f"\nRating scale (0-100):")
    print(f"  100: Native-like, no errors")
    print(f"  80-99: Very good, minor issues")
    print(f"  60-79: Good, some noticeable errors")
    print(f"  40-59: Fair, several errors")
    print(f"  20-39: Poor, frequent errors")
    print(f"  0-19: Very poor, unintelligible")
    print(f"\nPress Enter to play, then type your score (or 'q' to quit)")
    print(f"{'='*60}\n")

    ratings = []
    existing = set()

    # Load existing ratings to allow resuming
    if output_path.exists():
        with open(output_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["rater_id"] == rater_id:
                    existing.add(row["utterance_id"])
                    ratings.append(row)

    for i, rec_path in enumerate(recordings):
        utterance_id = rec_path.stem

        if utterance_id in existing:
            print(f"  [{i+1}/{len(recordings)}] {rec_path.name} — already rated, skipping")
            continue

        print(f"\n  [{i+1}/{len(recordings)}] {rec_path.name}")
        input("  Press Enter to play...")

        played = play_audio(rec_path)
        if not played:
            print(f"  (Could not auto-play. Listen to: {rec_path})")

        while True:
            score_input = input("  Your score (0-100, or 'r' to replay, 'q' to quit): ").strip()

            if score_input.lower() == "q":
                print("\nQuitting. Progress saved.")
                _save_ratings(ratings, output_path)
                return

            if score_input.lower() == "r":
                play_audio(rec_path)
                continue

            try:
                score = int(score_input)
                if 0 <= score <= 100:
                    break
                print("  Score must be between 0 and 100")
            except ValueError:
                print("  Please enter a number (0-100)")

        ratings.append({
            "rater_id": rater_id,
            "utterance_id": utterance_id,
            "score": score,
            "rated_at": datetime.now().isoformat(),
        })
        print(f"  → Recorded: {score}/100")

    _save_ratings(ratings, output_path)
    print(f"\n{'='*60}")
    print(f"DONE — {len(ratings)} ratings saved to {output_path}")
    print(f"{'='*60}")


def _save_ratings(ratings: list[dict], output_path: Path):
    """Save ratings to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["rater_id", "utterance_id", "score", "rated_at"]
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ratings)


def main():
    parser = argparse.ArgumentParser(description="Collect human pronunciation ratings")
    parser.add_argument("--recordings-dir", type=Path, default=Path("uploads/recordings"))
    parser.add_argument("--output", type=Path, default=Path("tests/eval/gold_dataset/human_ratings.csv"))
    parser.add_argument("--rater-id", type=str, default="rater_1")
    args = parser.parse_args()

    collect_ratings(args.recordings_dir, args.output, args.rater_id)


if __name__ == "__main__":
    main()
