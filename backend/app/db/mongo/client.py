"""
Motor (async MongoDB) client and database accessor.
The client is initialised at app startup and closed at shutdown.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.settings import settings

_client: AsyncIOMotorClient | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    """Return the module-level Motor client (initialised at startup)."""
    if _client is None:
        raise RuntimeError("MongoDB client has not been initialised. Call init_mongo() first.")
    return _client


def get_mongo_db() -> AsyncIOMotorDatabase:
    """Return the application's MongoDB database handle."""
    return get_mongo_client()[settings.mongo_database]


async def init_mongo() -> None:
    """Create the Motor client. Called once during app lifespan startup."""
    global _client
    _client = AsyncIOMotorClient(settings.mongo_uri)
    # Trigger an early connection check
    await _client.admin.command("ping")


async def close_mongo() -> None:
    """Close the Motor client. Called once during app lifespan shutdown."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
