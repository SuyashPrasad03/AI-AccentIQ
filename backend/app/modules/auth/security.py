"""
Cryptographic helpers for the auth module.

Responsibilities:
  - Password hashing / verification (argon2)
  - JWT access-token creation / validation
  - Opaque refresh-token generation and hashing
  - OTP generation and hashing
  - Anonymous session cookie signing (itsdangerous TimestampSigner)
"""

import hashlib
import hmac
import secrets
import string
from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.core.settings import settings

# ── Password hashing ─────────────────────────────────────────────────────────

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── JWT access tokens ────────────────────────────────────────────────────────

_JWT_ALGORITHM = "HS256"


def create_access_token(user_id: str) -> str:
    """Return a signed JWT valid for `jwt_access_token_expire_minutes`."""
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.
    Raises jwt.InvalidTokenError subtypes on failure.
    """
    return jwt.decode(token, settings.jwt_secret, algorithms=[_JWT_ALGORITHM])


# ── Refresh tokens ───────────────────────────────────────────────────────────

def generate_refresh_token() -> str:
    """Return a 64-byte cryptographically random hex string (opaque)."""
    return secrets.token_hex(64)


def hash_refresh_token(token: str) -> str:
    """Return SHA-256 hex digest of the raw token — stored in DB."""
    return hashlib.sha256(token.encode()).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)


# ── OTP generation ───────────────────────────────────────────────────────────

_OTP_ALPHABET = string.digits  # 6 numeric digits


def generate_otp() -> str:
    """Return a 6-digit OTP string."""
    return "".join(secrets.choice(_OTP_ALPHABET) for _ in range(6))


def hash_otp(otp: str) -> str:
    """Return bcrypt hash of the OTP for storage (uses passlib argon2)."""
    return _pwd_context.hash(otp)


def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── Anonymous session cookie ─────────────────────────────────────────────────

def generate_anon_session_id() -> str:
    """Return a 32-byte cryptographically random hex string for anon cookies."""
    return secrets.token_hex(32)


def sign_anon_session_id(session_id: str) -> str:
    """
    Return an HMAC-SHA256 signed value: "<session_id>.<signature>".
    This prevents trivial forgery of the anon_session_id cookie value.
    """
    sig = hmac.new(
        settings.jwt_secret.encode(),
        session_id.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{session_id}.{sig}"


def unsign_anon_session_id(signed: str) -> str | None:
    """
    Verify the HMAC signature and return the raw session_id, or None if invalid.
    Uses constant-time comparison to prevent timing attacks.
    """
    try:
        session_id, sig = signed.rsplit(".", 1)
    except ValueError:
        return None
    expected_sig = hmac.new(
        settings.jwt_secret.encode(),
        session_id.encode(),
        hashlib.sha256,
    ).hexdigest()
    if hmac.compare_digest(sig, expected_sig):
        return session_id
    return None


# ── Device fingerprint (soft, privacy-safe) ──────────────────────────────────

def compute_ip_hash(ip: str, user_agent: str) -> str:
    """
    Return a SHA-256 hex digest of IP + User-Agent.
    Used as a secondary signal — not sent to any third party,
    not stored as PII, and deliberately limited (no JS fingerprinting).
    """
    raw = f"{ip}|{user_agent}"
    return hashlib.sha256(raw.encode()).hexdigest()
