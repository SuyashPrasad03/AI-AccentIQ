"""
Application factory for the AI Pronunciation Coach backend.

Usage:
    uvicorn app.main:app --reload

Tests can spin up isolated instances via:
    from app.main import create_app
    app = create_app()
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.exceptions import AppException, app_exception_handler, unhandled_exception_handler
from app.core.logging import configure_logging, get_logger
from app.core.settings import settings
from app.db.mongo.client import close_mongo, init_mongo
from app.modules.auth.router import router as auth_router
from app.modules.compliance.router import router as compliance_router
from app.modules.health.router import router as health_router
from app.modules.quota.router import router as quota_router
from app.modules.upload.router import router as upload_router
from app.modules.transcription.router import router as transcription_router

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
        version="0.2.0",
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
    app.include_router(auth_router)       # /auth/*
    app.include_router(quota_router)      # /quota/*
    app.include_router(compliance_router) # /consent/*
    app.include_router(upload_router)     # /recordings/*
    app.include_router(transcription_router) # /recordings/{id}/status, /recordings/{id}/transcript

    # Future modules (uncomment as phases are implemented):
    # app.include_router(recordings_router, prefix="/recordings")
    # app.include_router(practice_router, prefix="/practice")
    # app.include_router(progress_router, prefix="/progress")
    # app.include_router(assistant_router, prefix="/assistant")

    logger.info("app_created", routers=["health", "auth", "quota", "compliance", "recordings"])
    return app


# Module-level app instance used by Uvicorn
app = create_app()
