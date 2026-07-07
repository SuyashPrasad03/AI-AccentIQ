"""
Local filesystem storage backend.

Files are stored under `settings.storage_local_root` (default: /app/storage).
In Docker the volume is mounted at that path. In production, swap to S3Backend.
"""

import os
from pathlib import Path

from app.core.logging import get_logger
from app.core.settings import settings
from app.modules.upload.storage.base import StorageBackend

logger = get_logger(__name__)


class LocalDiskBackend(StorageBackend):
    def __init__(self, root: str | None = None) -> None:
        self._root = Path(root or settings.storage_local_root)
        self._root.mkdir(parents=True, exist_ok=True)

    async def save(self, data: bytes, filename: str, subdirectory: str = "") -> str:
        target_dir = self._root / subdirectory
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / filename
        target_path.write_bytes(data)

        # Return the relative path from root
        relative = str(target_path.relative_to(self._root))
        logger.info("file_saved", path=relative, size=len(data))
        return relative

    async def delete(self, relative_path: str) -> bool:
        full = self._root / relative_path
        if full.exists():
            full.unlink()
            logger.info("file_deleted", path=relative_path)
            return True
        logger.warning("file_not_found_for_deletion", path=relative_path)
        return False

    async def exists(self, relative_path: str) -> bool:
        return (self._root / relative_path).exists()

    def get_full_path(self, relative_path: str) -> str:
        return str(self._root / relative_path)


def get_storage_backend() -> StorageBackend:
    """
    Factory: return the configured storage backend.
    Currently only 'local' is implemented; 's3' is a documented upgrade path.
    """
    if settings.storage_backend == "local":
        return LocalDiskBackend()
    # Future: elif settings.storage_backend == "s3": return S3Backend(...)
    raise ValueError(f"Unknown storage backend: {settings.storage_backend}")
