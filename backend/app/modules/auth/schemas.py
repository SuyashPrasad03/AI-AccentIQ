"""
Pydantic request / response schemas for the auth module.
Every endpoint uses these — never raw dicts.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Request schemas ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr

    model_config = {"str_strip_whitespace": True}


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_not_trivial(cls, v: str) -> str:
        if v.isdigit():
            raise ValueError("Password must contain at least one non-digit character.")
        return v

    model_config = {"str_strip_whitespace": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

    model_config = {"str_strip_whitespace": True}


class RefreshRequest(BaseModel):
    """Body-based refresh — the refresh token is read from the httpOnly cookie,
    but this schema is kept for any clients that prefer body delivery."""
    pass  # Token comes from cookie; body is empty


class SetPasswordRequest(BaseModel):
    """Used when a verified user wants to change their password later."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def new_password_not_trivial(cls, v: str) -> str:
        if v.isdigit():
            raise ValueError("Password must contain at least one non-digit character.")
        return v


# ── Response schemas ──────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: str
    email: str
    email_verified_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None  # Included for cross-domain clients that can't use cookies
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserOut


class RegisterResponse(BaseModel):
    message: str
    email: str


class LogoutResponse(BaseModel):
    message: str
