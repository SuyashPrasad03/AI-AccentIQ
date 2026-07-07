"""
GET /health — liveness + dependency probe.

Returns the connection status of MySQL and MongoDB without raising a 500
if a dependency is down — callers inspect the individual status fields.
"""

import asyncio
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.core.logging import get_logger
from app.db.mongo.client import get_mongo_client
from app.db.mysql.base import engine

router = APIRouter(tags=["health"])
logger = get_logger(__name__)

StatusLiteral = Literal["connected", "disconnected"]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    mysql: StatusLiteral
    mongo: StatusLiteral


async def _check_mysql() -> StatusLiteral:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "connected"
    except Exception as exc:
        logger.warning("mysql_health_check_failed", error=str(exc))
        return "disconnected"


async def _check_mongo() -> StatusLiteral:
    try:
        client = get_mongo_client()
        await client.admin.command("ping")
        return "connected"
    except Exception as exc:
        logger.warning("mongo_health_check_failed", error=str(exc))
        return "disconnected"


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health() -> HealthResponse:
    """
    Check the health of the application and its backing services.

    - **mysql**: whether a MySQL connection can be established.
    - **mongo**: whether MongoDB responds to a ping.
    - **status**: `ok` only when both are connected; `degraded` otherwise.
    """
    mysql_status, mongo_status = await asyncio.gather(
        _check_mysql(),
        _check_mongo(),
    )

    overall = "ok" if mysql_status == "connected" and mongo_status == "connected" else "degraded"

    logger.info("health_check", status=overall, mysql=mysql_status, mongo=mongo_status)

    return HealthResponse(status=overall, mysql=mysql_status, mongo=mongo_status)
