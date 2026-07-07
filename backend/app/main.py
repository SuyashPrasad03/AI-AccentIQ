"""
Application factory for the AI Pronunciation Coach backend.

Usage:
    uvicorn app.main:app --reload

Tests can spin up isolated instances via:
    from app.main import create_app
    app = create_app()
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException, app_exception_handler, unhandled_exception_handler
from app.core.logging import configure_logging, get_logger
from app.core.settings import settings
from app.db.mongo.client import close_mongo, init_mongo
from app.modules.health.router import router as health_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of shared resources."""
    configure_logging()
    logger.info("startup", env=settings.app_env)

    # Initialise MongoDB connection
    await init_mongo()
    logger.info("mongo_connected")

    yield  # Application is running

    # Graceful shutdown
    await close_mongo()
    logger.info("shutdown")


def create_app() -> FastAPI:
    """
    App factory — returns a configured FastAPI application.
    Keeping this as a factory (rather than a module-level app object) allows
    tests to instantiate isolated copies with different settings.
    """
    app = FastAPI(
        title="AI Pronunciation Coach",
        description="Backend API for the AI-powered pronunciation coaching platform.",
        version="0.1.0",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global exception handlers ─────────────────────────────
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # ── Routers ───────────────────────────────────────────────
    app.include_router(health_router)

    # Future modules will be registered here as phases are implemented:
    # app.include_router(auth_router, prefix="/auth")
    # app.include_router(quota_router, prefix="/quota")
    # app.include_router(recordings_router, prefix="/recordings")
    # app.include_router(practice_router, prefix="/practice")
    # app.include_router(progress_router, prefix="/progress")
    # app.include_router(assistant_router, prefix="/assistant")
    # app.include_router(compliance_router)

    logger.info("app_created", routers=["health"])
    return app


# Module-level app instance used by Uvicorn
app = create_app()
