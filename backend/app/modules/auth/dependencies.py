"""
FastAPI dependencies for identity resolution.

`get_current_user()`   — requires a valid JWT access token; raises 401 otherwise.
`get_current_identity()` — resolves either an authenticated User or an anonymous
                           session ID uniformly. Never raises for anonymous callers.
                           Used by every endpoint that needs to know "who is asking"
                           (upload, quota check, consent recording, etc.).

Both are usable as FastAPI dependencies via Depends().
"""

from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.core.logging import get_logger
from app.db.mysql.base import get_db
from app.modules.auth.models import User
from app.modules.auth.schemas import UserOut
from app.modules.auth.security import decode_access_token, unsign_anon_session_id
from app.modules.auth.service import get_user_by_id

logger = get_logger(__name__)


@dataclass
class Identity:
    """
    Uniform identity object resolved for every request.

    Exactly one of `user` / `anon_session_id` will be set:
      - Authenticated:  identity.user is a User ORM instance, anon_session_id is None
      - Anonymous:      identity.user is None, anon_session_id is a raw session ID str
    """

    user: User | None
    anon_session_id: str | None

    @property
    def is_authenticated(self) -> bool:
        return self.user is not None

    @property
    def user_id(self) -> str | None:
        return self.user.id if self.user else None

    @property
    def display_name(self) -> str:
        """Human-readable label for logging."""
        if self.user:
            return f"user:{self.user.id}"
        return f"anon:{self.anon_session_id}"


def _extract_bearer_token(request: Request) -> str | None:
    """Pull the JWT from the Authorization header, or None if absent/malformed."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[len("Bearer "):]
        return token if token else None
    return None


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency that requires a valid authenticated user.
    Raises AuthenticationError (HTTP 401) if the token is missing or invalid.
    """
    token = _extract_bearer_token(request)
    if not token:
        raise AuthenticationError(message="Access token required.")

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise AuthenticationError(message="Access token has expired.")
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError(message=f"Invalid access token: {exc}")

    user_id: str = payload.get("sub", "")
    if not user_id:
        raise AuthenticationError(message="Malformed token: missing subject.")

    user = await get_user_by_id(user_id, db)
    return user


async def get_current_identity(
    request: Request,
    db: AsyncSession = Depends(get_db),
    anon_session_cookie: str | None = Cookie(default=None, alias="anon_session_id"),
) -> Identity:
    """
    Resolve the caller's identity — authenticated user or anonymous session.

    Resolution order:
      1. JWT in Authorization header  → authenticated Identity
      2. Signed anon_session_id cookie → anonymous Identity with that session ID
      3. No credential at all          → anonymous Identity with None session ID
         (the quota / consent layer will assign a session ID and set the cookie)
    """
    token = _extract_bearer_token(request)
    if token:
        try:
            payload = decode_access_token(token)
            user_id: str = payload.get("sub", "")
            if user_id:
                user = await get_user_by_id(user_id, db)
                # Also preserve anon_session_id so consent lookup can find pre-login consent
                anon_id = None
                if anon_session_cookie:
                    anon_id = unsign_anon_session_id(anon_session_cookie)
                return Identity(user=user, anon_session_id=anon_id)
        except (jwt.InvalidTokenError, Exception):
            # Bad token: fall through to anonymous handling
            pass

    # Try the signed anon cookie
    if anon_session_cookie:
        raw_id = unsign_anon_session_id(anon_session_cookie)
        if raw_id:
            return Identity(user=None, anon_session_id=raw_id)

    # No usable credential
    return Identity(user=None, anon_session_id=None)


# Typed shorthand for use in endpoint signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentIdentity = Annotated[Identity, Depends(get_current_identity)]
