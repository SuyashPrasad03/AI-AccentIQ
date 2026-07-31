"""
Scoring service — backward-compatible entry point.

Phase 24 refactored scoring into scoring_service.py (the orchestrator).
This module re-exports the public API so existing imports continue to work.
"""

from app.modules.scoring.scoring_service import (
    run_scoring_job,
    get_score_for_recording,
)

__all__ = ["run_scoring_job", "get_score_for_recording"]
