"""
Alembic migration environment.
Configured for async SQLAlchemy (aiomysql driver).
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.settings import settings
# Import Base so all models are registered before autogenerate runs.
# Add new model imports here as each phase introduces tables.
from app.db.mysql.base import Base  # noqa: F401 — triggers model registration
from app.modules.auth.models import OtpCode, RefreshToken, User  # noqa: F401
from app.modules.compliance.models import ConsentEvent  # noqa: F401
from app.modules.quota.models import AnonymousUsage  # noqa: F401

# Alembic config object from alembic.ini
alembic_config = context.config

# Set up Python logging from the ini file's [loggers] section
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

# SQLAlchemy metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DB connection; emits SQL to stdout)."""
    url = settings.mysql_dsn.replace("mysql+pymysql://", "mysql+aiomysql://")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations against a live async engine."""
    url = settings.mysql_dsn.replace("mysql+pymysql://", "mysql+aiomysql://")
    async_engine = create_async_engine(url)
    async with async_engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await async_engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
