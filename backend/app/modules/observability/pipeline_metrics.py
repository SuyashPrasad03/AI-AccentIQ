"""
Phase 32 — Pipeline Metrics Instrumentation

Wraps each AI pipeline stage with latency/cost/metadata logging.
Provides a decorator and context manager for instrumenting any function.

Stages tracked:
  - transcription: WhisperX/Deepgram ASR
  - gop_scoring: wav2vec2-CTC GOP computation
  - error_classification: LightGBM inference
  - feedback_generation: OpenRouter/Gemini LLM call
  - rag_retrieval: vector search + LLM synthesis
  - streaming_scoring: WebSocket incremental scoring

Each metric record includes: stage, latency_ms, cost_usd (for LLM calls),
metadata (model, tokens, recording_id, etc.), timestamp.
"""

import time
import functools
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# In-memory buffer for metrics (flushed to DB periodically or per-request)
_metrics_buffer: list[dict] = []
_BUFFER_FLUSH_SIZE = 20


async def record_metric(
    stage: str,
    latency_ms: float,
    cost_usd: float | None = None,
    metadata: dict | None = None,
) -> None:
    """
    Record a pipeline metric. Buffers in memory and flushes to MongoDB.
    """
    metric = {
        "stage": stage,
        "latency_ms": round(latency_ms, 1),
        "cost_usd": round(cost_usd, 6) if cost_usd else None,
        "metadata": metadata or {},
        "timestamp": datetime.now(UTC),
    }

    _metrics_buffer.append(metric)

    # Flush if buffer is full
    if len(_metrics_buffer) >= _BUFFER_FLUSH_SIZE:
        await flush_metrics()


async def flush_metrics() -> int:
    """Flush buffered metrics to MongoDB. Returns count flushed."""
    global _metrics_buffer

    if not _metrics_buffer:
        return 0

    to_flush = _metrics_buffer.copy()
    _metrics_buffer = []

    try:
        from app.db.mongo.client import get_mongo_db
        db = get_mongo_db()
        await db["pipeline_metrics"].insert_many(to_flush)
        logger.info("metrics_flushed", count=len(to_flush))
        return len(to_flush)
    except Exception as exc:
        logger.error("metrics_flush_failed", error=str(exc), count=len(to_flush))
        # Put them back (best effort)
        _metrics_buffer.extend(to_flush)
        return 0


def track_latency(stage: str):
    """
    Decorator to track latency of a sync or async function.
    Records the metric after execution.
    """
    def decorator(func):
        if functools.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    await record_metric(stage, elapsed_ms)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            loop.create_task(record_metric(stage, elapsed_ms))
                        else:
                            loop.run_until_complete(record_metric(stage, elapsed_ms))
                    except RuntimeError:
                        _metrics_buffer.append({
                            "stage": stage,
                            "latency_ms": round(elapsed_ms, 1),
                            "cost_usd": None,
                            "metadata": {},
                            "timestamp": datetime.now(UTC),
                        })
            return sync_wrapper
    return decorator


@asynccontextmanager
async def track_stage(stage: str, metadata: dict | None = None):
    """
    Async context manager to track a pipeline stage.

    Usage:
        async with track_stage("gop_scoring", {"recording_id": "abc"}):
            result = compute_gop(...)
    """
    start = time.perf_counter()
    ctx: dict[str, Any] = {"cost_usd": None}
    try:
        yield ctx
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        merged_metadata = {**(metadata or {}), **{k: v for k, v in ctx.items() if k != "cost_usd"}}
        await record_metric(
            stage=stage,
            latency_ms=elapsed_ms,
            cost_usd=ctx.get("cost_usd"),
            metadata=merged_metadata,
        )


async def get_metrics_summary(hours: int = 24) -> dict:
    """
    Get aggregated metrics for the admin dashboard.
    Returns per-stage latency percentiles, cost totals, and request counts.
    """
    from app.db.mongo.client import get_mongo_db

    db = get_mongo_db()

    cutoff = datetime.now(UTC).replace(hour=0, minute=0, second=0)
    if hours < 24:
        import timedelta
        cutoff = datetime.now(UTC) - timedelta(hours=hours)

    cursor = db["pipeline_metrics"].find(
        {"timestamp": {"$gte": cutoff}}
    ).sort("timestamp", -1).limit(5000)

    # Aggregate per stage
    from collections import defaultdict
    stage_data = defaultdict(lambda: {"latencies": [], "costs": [], "count": 0})

    async for doc in cursor:
        stage = doc.get("stage", "unknown")
        stage_data[stage]["latencies"].append(doc.get("latency_ms", 0))
        if doc.get("cost_usd"):
            stage_data[stage]["costs"].append(doc["cost_usd"])
        stage_data[stage]["count"] += 1

    import numpy as np

    summary = {}
    total_cost = 0.0
    total_requests = 0

    for stage, data in stage_data.items():
        latencies = data["latencies"]
        costs = data["costs"]

        summary[stage] = {
            "count": data["count"],
            "latency_p50": round(float(np.percentile(latencies, 50)), 1) if latencies else 0,
            "latency_p95": round(float(np.percentile(latencies, 95)), 1) if latencies else 0,
            "latency_mean": round(float(np.mean(latencies)), 1) if latencies else 0,
            "cost_total": round(sum(costs), 4) if costs else 0,
            "cost_mean": round(float(np.mean(costs)), 6) if costs else 0,
        }
        total_cost += sum(costs)
        total_requests += data["count"]

    return {
        "stages": summary,
        "total_cost_usd": round(total_cost, 4),
        "total_requests": total_requests,
        "period_hours": hours,
    }
