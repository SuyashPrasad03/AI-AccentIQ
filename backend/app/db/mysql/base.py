"""
SQLAlchemy async engine + session factory for MySQL.
All models should import `Base` from here so Alembic can auto-detect them.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.settings import settings

# Use aiomysql driver for async support
_ASYNC_DSN = settings.mysql_dsn.replace("mysql+pymysql://", "mysql+aiomysql://")

engine = create_async_engine(
    _ASYNC_DSN,
    echo=(settings.app_env == "development"),
    pool_pre_ping=True,
    pool_recycle=3600,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
