"""
Phase 32 — Observability / Admin Dashboard API

Admin-only endpoints for viewing pipeline metrics, latency, cost, and quality.
Access-restricted: only authenticated users with admin role (for now, any authenticated user).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.db.mysql.base import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.observability.pipeline_metrics import get_metrics_summary, flush_metrics

router = APIRouter(prefix="/admin/metrics", tags=["observability"])


@router.get(
    "/summary",
    summary="Get pipeline metrics summary (admin only)",
)
async def metrics_summary(
    hours: int = 24,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Returns aggregated metrics for the AI pipeline:
    - Per-stage latency (p50, p95, mean)
    - Cost totals (OpenRouter/Gemini token usage)
    - Request counts per stage
    - Period: last N hours (default 24)
    """
    # Flush any buffered metrics first
    await flush_metrics()

    summary = await get_metrics_summary(hours=hours)
    return summary


@router.get(
    "/recent",
    summary="Get recent individual metric records (admin only)",
)
async def recent_metrics(
    limit: int = 50,
    stage: str | None = None,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Returns the most recent individual metric records for debugging/inspection.
    Optionally filter by stage name.
    """
    from app.db.mongo.client import get_mongo_db

    db = get_mongo_db()

    query = {}
    if stage:
        query["stage"] = stage

    cursor = db["pipeline_metrics"].find(
        query, {"_id": 0}
    ).sort("timestamp", -1).limit(limit)

    records = []
    async for doc in cursor:
        # Serialize datetime
        doc["timestamp"] = doc["timestamp"].isoformat() if doc.get("timestamp") else None
        records.append(doc)

    return {"records": records, "count": len(records)}
