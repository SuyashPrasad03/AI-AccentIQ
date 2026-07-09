"""
Application factory for the AI AccentIQ backend.

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

# These may fail if optional deps aren't installed — graceful fallback
try:
    from app.modules.transcription.router import router as transcription_router
except ImportError:
    transcription_router = None
try:
    from app.modules.scoring.router import router as scoring_router
except ImportError:
    scoring_router = None
try:
    from app.modules.feedback.router import router as feedback_router
except ImportError:
    feedback_router = None
try:
    from app.modules.practice_generator.router import router as practice_router
except ImportError:
    practice_router = None
try:
    from app.modules.progress.router import router as progress_router
except ImportError:
    progress_router = None
try:
    from app.modules.rag.router import router as rag_router
except ImportError:
    rag_router = None
from app.modules.rag.router import router as rag_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of shared resources."""
    configure_logging()
    logger.info("startup", env=settings.app_env)

    # Initialise MongoDB connection
    await init_mongo()
    logger.info("mongo_connected")

    # Index knowledge base for RAG assistant (idempotent — only ingests if empty)
    from app.modules.rag.ingest import ensure_kb_indexed
    await ensure_kb_indexed()

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
        title="AI AccentIQ",
        description="Backend API for the AI-powered pronunciation coaching platform.",
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────
    # Allow all origins for now (deployment debugging)
    # Lock down to specific origins in production later
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
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
    if transcription_router: app.include_router(transcription_router)
    if scoring_router: app.include_router(scoring_router)
    if feedback_router: app.include_router(feedback_router)
    if practice_router: app.include_router(practice_router)
    if progress_router: app.include_router(progress_router)
    if rag_router: app.include_router(rag_router)

    # Future modules (uncomment as phases are implemented):
    # app.include_router(recordings_router, prefix="/recordings")
    # app.include_router(practice_router, prefix="/practice")
    # app.include_router(progress_router, prefix="/progress")
    # app.include_router(assistant_router, prefix="/assistant")

    logger.info("app_created", routers=["health", "auth", "quota", "compliance", "recordings"])
    return app


# Module-level app instance used by Uvicorn
app = create_app()
