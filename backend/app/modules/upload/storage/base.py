"""
Abstract base class for the storage backend.

Implementations must support:
  - save: write raw bytes to a path, return the relative storage path
  - delete: remove a file by its relative storage path
  - exists: check if a file exists
  - get_full_path: resolve relative path to absolute filesystem/URL path

This is the seam that lets us swap LocalDisk for S3 without touching service.py.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, data: bytes, filename: str, subdirectory: str = "") -> str:
        """
        Persist `data` to storage under `subdirectory/filename`.
        Returns the relative storage path (e.g. "recordings/abc123.wav").
        """

    @abstractmethod
    async def delete(self, relative_path: str) -> bool:
        """
        Delete the file at `relative_path`.
        Returns True if deletion succeeded, False if file didn't exist.
        """

    @abstractmethod
    async def exists(self, relative_path: str) -> bool:
        """Check whether a file exists at the given relative path."""

    @abstractmethod
    def get_full_path(self, relative_path: str) -> str:
        """Resolve relative path to absolute path / URL for downstream consumers."""
