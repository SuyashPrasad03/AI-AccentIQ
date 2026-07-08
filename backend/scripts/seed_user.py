"""
Seed script — creates a pre-registered test user.
Run with: python -m scripts.seed_user

Creates:
  Email: test@pronunciation.coach
  Password: Test1234!
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import UTC, datetime

from sqlalchemy import select

from app.core.settings import settings
from app.db.mysql.base import AsyncSessionLocal
from app.modules.auth.models import User
from app.modules.auth.security import hash_password


SEED_EMAIL = "test@pronunciation.coach"
SEED_PASSWORD = "Test1234!"


async def seed():
    async with AsyncSessionLocal() as db:
        # Check if already exists
        result = await db.execute(
            select(User).where(User.email == SEED_EMAIL)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"✓ Seed user already exists: {SEED_EMAIL}")
            return

        user = User(
            email=SEED_EMAIL,
            password_hash=hash_password(SEED_PASSWORD),
            email_verified_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db.add(user)
        await db.commit()
        print(f"✓ Seed user created!")
        print(f"  Email:    {SEED_EMAIL}")
        print(f"  Password: {SEED_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
