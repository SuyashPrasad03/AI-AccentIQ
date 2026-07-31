"""
Phase 31 — Error History Aggregator

Aggregates a user's pronunciation error history across all sessions,
clusters recurring error patterns, and prioritizes by frequency × severity
(GOP gap magnitude).

This is the "long-term memory" component of the agentic planner:
  - Looks across ALL recordings, not just the most recent
  - Identifies persistent weak patterns (not one-off errors)
  - Weighs severity (a large GOP gap is more important than a small one)
  - Groups by phoneme + error type for targeted practice planning
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from app.core.logging import get_logger
from app.db.mongo.client import get_mongo_db

logger = get_logger(__name__)


@dataclass
class PhonemeErrorCluster:
    """A cluster of recurring errors for a specific phoneme."""
    phoneme: str
    occurrence_count: int  # How many recordings this phoneme was flagged
    mean_gop_gap: float  # Average severity
    max_gop_gap: float  # Worst instance
    common_substitution: str | None = None  # Most frequent substitution
    error_types: dict = field(default_factory=dict)  # {error_type: count}
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    priority_score: float = 0.0  # frequency × severity

    def compute_priority(self):
        """Priority = frequency × normalized severity."""
        # Normalize gap to 0-1 range (gap of 5+ is severe)
        severity = min(self.mean_gop_gap / 5.0, 1.0)
        # Frequency factor (log scale, diminishing returns after 5)
        import math
        frequency = min(math.log2(self.occurrence_count + 1) / 3.0, 1.0)
        self.priority_score = round(frequency * severity * 100, 1)


@dataclass
class ErrorHistorySummary:
    """Complete error history summary for a user."""
    total_recordings: int
    total_phonemes_analyzed: int
    weak_phoneme_clusters: list[PhonemeErrorCluster]
    top_priorities: list[str]  # Top 5 phonemes to focus on
    improvement_trend: str  # "improving" | "stable" | "regressing" | "insufficient_data"


async def aggregate_error_history(
    user_id: str | None = None,
    anon_session_id: str | None = None,
) -> ErrorHistorySummary:
    """
    Aggregate the full error history for a user across all recordings.
    Returns clustered, prioritized error patterns.
    """
    db = get_mongo_db()

    # Query all phoneme analyses
    # In a production system, this would filter by user_id via a join
    # For now, get all recent analyses (ordered by date)
    cursor = db["phoneme_analysis"].find(
        {},
        {"words": 1, "weak_phonemes": 1, "gop_raw_scores": 1,
         "overall_score": 1, "created_at": 1, "recording_id": 1}
    ).sort("created_at", -1).limit(50)

    # Aggregate per-phoneme error data
    phoneme_data = defaultdict(lambda: {
        "occurrences": 0,
        "gaps": [],
        "substitutions": defaultdict(int),
        "error_types": defaultdict(int),
        "dates": [],
    })

    total_recordings = 0
    total_phonemes = 0
    overall_scores = []

    async for doc in cursor:
        total_recordings += 1
        created_at = doc.get("created_at")
        overall_scores.append(doc.get("overall_score", 0))

        # From weak_phonemes list
        for ph in doc.get("weak_phonemes", []):
            phoneme_data[ph]["occurrences"] += 1
            if created_at:
                phoneme_data[ph]["dates"].append(created_at)

        # From GOP raw scores (more detailed)
        for word_data in doc.get("gop_raw_scores", []):
            for ph_data in word_data.get("phonemes", []):
                phoneme = ph_data.get("phoneme", "")
                gap = ph_data.get("gap", 0.0)
                max_post = ph_data.get("max_posterior_phoneme", "")

                if gap > 1.5 and phoneme:  # Only count significant errors
                    total_phonemes += 1
                    phoneme_data[phoneme]["gaps"].append(gap)
                    if max_post and max_post != phoneme:
                        phoneme_data[phoneme]["substitutions"][max_post] += 1

        # From word-level data
        for word in doc.get("words", []):
            if word.get("detected_issue") == "mispronounced":
                for ph in word.get("expected_phonemes", []):
                    phoneme_data[ph]["error_types"]["mispronounced"] += 1

    # Build clusters
    clusters = []
    for phoneme, data in phoneme_data.items():
        if data["occurrences"] < 1 and not data["gaps"]:
            continue

        # Find most common substitution
        common_sub = None
        if data["substitutions"]:
            common_sub = max(data["substitutions"], key=data["substitutions"].get)

        cluster = PhonemeErrorCluster(
            phoneme=phoneme,
            occurrence_count=max(data["occurrences"], len(data["gaps"])),
            mean_gop_gap=sum(data["gaps"]) / len(data["gaps"]) if data["gaps"] else 2.0,
            max_gop_gap=max(data["gaps"]) if data["gaps"] else 2.0,
            common_substitution=common_sub,
            error_types=dict(data["error_types"]),
            first_seen=min(data["dates"]) if data["dates"] else None,
            last_seen=max(data["dates"]) if data["dates"] else None,
        )
        cluster.compute_priority()
        clusters.append(cluster)

    # Sort by priority
    clusters.sort(key=lambda c: c.priority_score, reverse=True)

    # Determine improvement trend
    trend = _compute_trend(overall_scores)

    # Top priorities
    top_priorities = [c.phoneme for c in clusters[:5]]

    summary = ErrorHistorySummary(
        total_recordings=total_recordings,
        total_phonemes_analyzed=total_phonemes,
        weak_phoneme_clusters=clusters,
        top_priorities=top_priorities,
        improvement_trend=trend,
    )

    logger.info(
        "error_history_aggregated",
        recordings=total_recordings,
        clusters=len(clusters),
        top_priorities=top_priorities,
        trend=trend,
    )

    return summary


def _compute_trend(scores: list[float]) -> str:
    """Determine if the user is improving, stable, or regressing."""
    if len(scores) < 4:
        return "insufficient_data"

    # Compare first half to second half
    mid = len(scores) // 2
    recent_avg = sum(scores[:mid]) / mid  # Most recent (sorted desc)
    older_avg = sum(scores[mid:]) / (len(scores) - mid)

    diff = recent_avg - older_avg
    if diff > 5:
        return "improving"
    elif diff < -5:
        return "regressing"
    return "stable"
