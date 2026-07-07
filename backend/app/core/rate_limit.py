"""
Simple in-memory OTP rate limiter.

Tracks OTP send requests per email address within a sliding 1-hour window.
This is deliberately Redis-free (fine at assessment scale).
Upgrade path: swap the in-memory store for Redis with a sorted-set TTL window.

Thread/async safety: a single asyncio event loop is assumed (FastAPI's default).
The dict operations are GIL-protected in CPython, so no explicit lock is needed.
"""

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from app.core.settings import settings


class OtpRateLimiter:
    def __init__(self) -> None:
        # email → list of UTC datetimes when OTPs were sent in the current window
        self._sends: dict[str, list[datetime]] = defaultdict(list)

    def _prune(self, email: str) -> None:
        """Remove timestamps older than 1 hour."""
        cutoff = datetime.now(UTC) - timedelta(hours=1)
        self._sends[email] = [t for t in self._sends[email] if t > cutoff]

    def is_allowed(self, email: str) -> bool:
        """Return True if another OTP may be sent to this email address."""
        self._prune(email)
        return len(self._sends[email]) < settings.otp_rate_limit_per_hour

    def record(self, email: str) -> None:
        """Record that an OTP was just sent."""
        self._sends[email].append(datetime.now(UTC))

    def remaining(self, email: str) -> int:
        """How many more OTPs can be sent in the current window."""
        self._prune(email)
        return max(0, settings.otp_rate_limit_per_hour - len(self._sends[email]))


# Module-level singleton shared across requests within one process.
otp_rate_limiter = OtpRateLimiter()
