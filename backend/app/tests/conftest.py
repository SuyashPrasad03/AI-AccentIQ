"""
Shared pytest fixtures and configuration for the test suite.
"""

import pytest


# Make pytest-asyncio work with async tests without per-test decorators
pytest_plugins = ["pytest_asyncio"]
