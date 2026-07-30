"""
Phase 31 — Agentic Practice Plan Generator

Generates a structured, adaptive N-day practice plan based on the user's
cross-session error history. This is "agentic" in the legitimate sense:
  - Operates over persistent state (error history = long-term memory)
  - Makes a plan (not a single-turn answer)
  - Adapts on subsequent runs based on new data

The planner:
  1. Reads the aggregated error history (from error_history_aggregator)
  2. Prioritizes phonemes by frequency × severity
  3. Selects practice sentences from the curated bank (not hallucinated)
  4. Structures them into a day-by-day plan with checkpoints
  5. Adapts if re-run after new data (reprioritizes)
"""

import json
from datetime import date, timedelta, datetime, UTC
from dataclasses import dataclass, field
from pathlib import Path

from app.core.logging import get_logger
from app.db.mongo.client import get_mongo_db
from app.modules.practice_generator.error_history_aggregator import (
    ErrorHistorySummary,
    aggregate_error_history,
)

logger = get_logger(__name__)

SENTENCE_BANK_PATH = Path(__file__).resolve().parent / "practice_sentence_bank.json"
PLANS_COLLECTION = "practice_plans"
PLAN_DURATION_DAYS = 7  # Default plan length
SENTENCES_PER_DAY = 3
CHECKPOINT_INTERVAL_DAYS = 3  # Re-assess every 3 days


@dataclass
class PlanItem:
    """A single practice item within a day."""
    sentence: str
    target_phoneme: str
    focus_description: str
    difficulty: str  # "warmup" | "focus" | "challenge"


@dataclass
class PlanDay:
    """One day's practice within the plan."""
    day_number: int
    date: str
    focus_phonemes: list[str]
    items: list[PlanItem]
    is_checkpoint: bool = False  # True on checkpoint days


@dataclass
class PracticePlan:
    """A complete N-day practice plan."""
    plan_id: str
    user_id: str | None
    generated_at: datetime
    duration_days: int
    target_phonemes: list[str]
    days: list[PlanDay]
    progress_status: str  # "active" | "completed" | "superseded"
    improvement_trend: str
    total_items: int = 0

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "user_id": self.user_id,
            "generated_at": self.generated_at,
            "duration_days": self.duration_days,
            "target_phonemes": self.target_phonemes,
            "days": [
                {
                    "day_number": d.day_number,
                    "date": d.date,
                    "focus_phonemes": d.focus_phonemes,
                    "is_checkpoint": d.is_checkpoint,
                    "items": [
                        {
                            "sentence": item.sentence,
                            "target_phoneme": item.target_phoneme,
                            "focus_description": item.focus_description,
                            "difficulty": item.difficulty,
                        }
                        for item in d.items
                    ],
                }
                for d in self.days
            ],
            "progress_status": self.progress_status,
            "improvement_trend": self.improvement_trend,
            "total_items": self.total_items,
        }


def _load_sentence_bank() -> dict[str, list[str]]:
    """Load the curated practice sentence bank."""
    if not SENTENCE_BANK_PATH.exists():
        return {}
    with open(SENTENCE_BANK_PATH) as f:
        return json.load(f)


async def generate_practice_plan(
    user_id: str | None = None,
    anon_session_id: str | None = None,
    duration_days: int = PLAN_DURATION_DAYS,
) -> PracticePlan:
    """
    Generate a structured practice plan based on the user's error history.

    The plan:
      - Targets the top priority phonemes (max 3-4 per plan)
      - Structures practice across days with progressive difficulty
      - Includes checkpoints every 3 days for re-assessment
      - Uses only sentences from the curated bank (no hallucination)
    """
    import uuid

    # 1. Aggregate error history
    history = await aggregate_error_history(user_id, anon_session_id)

    # 2. Select target phonemes (top 3 priorities)
    target_phonemes = history.top_priorities[:3]
    if not target_phonemes:
        target_phonemes = ["θ", "ɹ"]  # Default starter targets

    # 3. Load sentence bank
    sentence_bank = _load_sentence_bank()

    # 4. Build day-by-day plan
    start_date = date.today()
    days = []

    for day_num in range(1, duration_days + 1):
        day_date = start_date + timedelta(days=day_num - 1)
        is_checkpoint = (day_num % CHECKPOINT_INTERVAL_DAYS == 0) or (day_num == duration_days)

        # Rotate focus across target phonemes
        focus_idx = (day_num - 1) % len(target_phonemes)
        primary_phoneme = target_phonemes[focus_idx]
        day_focus = [primary_phoneme]

        # Add secondary phoneme on some days
        if len(target_phonemes) > 1 and day_num % 2 == 0:
            secondary_idx = (focus_idx + 1) % len(target_phonemes)
            day_focus.append(target_phonemes[secondary_idx])

        # Select sentences from bank
        items = _select_day_items(primary_phoneme, day_focus, sentence_bank, day_num)

        days.append(PlanDay(
            day_number=day_num,
            date=day_date.isoformat(),
            focus_phonemes=day_focus,
            items=items,
            is_checkpoint=is_checkpoint,
        ))

    # 5. Build plan
    plan_id = str(uuid.uuid4())[:8]
    plan = PracticePlan(
        plan_id=plan_id,
        user_id=user_id,
        generated_at=datetime.now(UTC),
        duration_days=duration_days,
        target_phonemes=target_phonemes,
        days=days,
        progress_status="active",
        improvement_trend=history.improvement_trend,
        total_items=sum(len(d.items) for d in days),
    )

    # 6. Store in MongoDB
    await _store_plan(plan)

    logger.info(
        "practice_plan_generated",
        plan_id=plan_id,
        user_id=user_id,
        target_phonemes=target_phonemes,
        duration_days=duration_days,
        total_items=plan.total_items,
        trend=history.improvement_trend,
    )

    return plan


def _select_day_items(
    primary_phoneme: str,
    day_focus: list[str],
    sentence_bank: dict[str, list[str]],
    day_number: int,
) -> list[PlanItem]:
    """Select practice items for a given day from the sentence bank."""
    items = []
    sentences_used = set()

    # Warmup: easy sentence for primary phoneme
    primary_sentences = sentence_bank.get(primary_phoneme, [])
    if primary_sentences:
        idx = (day_number - 1) % len(primary_sentences)
        sentence = primary_sentences[idx]
        items.append(PlanItem(
            sentence=sentence,
            target_phoneme=primary_phoneme,
            focus_description=f"Focus on the /{primary_phoneme}/ sound. Say it slowly first.",
            difficulty="warmup",
        ))
        sentences_used.add(sentence)

    # Focus: another sentence for primary phoneme (different one)
    if len(primary_sentences) > 1:
        idx2 = (day_number) % len(primary_sentences)
        if primary_sentences[idx2] not in sentences_used:
            items.append(PlanItem(
                sentence=primary_sentences[idx2],
                target_phoneme=primary_phoneme,
                focus_description=f"Try this at natural speaking speed. Keep /{primary_phoneme}/ clear.",
                difficulty="focus",
            ))

    # Challenge: sentence from secondary phoneme (if any)
    if len(day_focus) > 1:
        secondary = day_focus[1]
        secondary_sentences = sentence_bank.get(secondary, [])
        if secondary_sentences:
            idx3 = (day_number + 2) % len(secondary_sentences)
            items.append(PlanItem(
                sentence=secondary_sentences[idx3],
                target_phoneme=secondary,
                focus_description=f"Challenge: now focus on /{secondary}/ while maintaining natural flow.",
                difficulty="challenge",
            ))

    return items


async def _store_plan(plan: PracticePlan):
    """Store the plan in MongoDB."""
    db = get_mongo_db()

    # Mark any previous active plans as superseded
    if plan.user_id:
        await db[PLANS_COLLECTION].update_many(
            {"user_id": plan.user_id, "progress_status": "active"},
            {"$set": {"progress_status": "superseded"}},
        )

    await db[PLANS_COLLECTION].insert_one(plan.to_dict())


async def get_active_plan(user_id: str | None = None) -> dict | None:
    """Get the user's current active practice plan."""
    if not user_id:
        return None

    db = get_mongo_db()
    return await db[PLANS_COLLECTION].find_one(
        {"user_id": user_id, "progress_status": "active"},
        sort=[("generated_at", -1)],
    )
