"""
Backward-compatible entry point for the scoring formula.

Phase 24 moved the original scoring logic to legacy_diff_scorer.py.
This module re-exports the public function so existing imports work.
"""

from app.modules.scoring.legacy_diff_scorer import score_recording_legacy as score_recording

__all__ = ["score_recording"]
