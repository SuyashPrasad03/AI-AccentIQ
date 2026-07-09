"""
Auth router — /auth/* endpoints.

  POST /auth/register       — send OTP to email
  POST /auth/verify-otp     — verify OTP + set password → issue tokens
  POST /auth/login          — email + password → issue tokens
  POST /auth/refresh        — rotate refresh token → new token pair
  POST /auth/logout         — revoke refresh token
  GET  /auth/me             — return current user (requires auth)
"""

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.core.settings import settings
from app.db.mysql.base import get_db
from app.modules.auth import service
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserOut,
    VerifyOtpRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_COOKIE = "refresh_token"
_COOKIE_MAX_AGE = settings.jwt_refresh_token_expire_days * 86_400  # seconds


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=settings.app_env != "development",
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=_REFRESH_COOKIE, path="/")


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=202,
    summary="Initiate email registration (sends OTP)",
)
async def register(
    body: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    email = await service.register_user(email=body.email, db=db, background_tasks=background_tasks)
    return RegisterResponse(
        message="Verification code sent. Please check your email.",
        email=email,
    )


@router.post(
    "/verify-otp",
    response_model=TokenResponse,
    summary="Verify OTP + set password → receive access token",
)
async def verify_otp(
    body: VerifyOtpRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user, access_token, refresh_plain = await service.verify_otp_and_create_user(
        email=body.email,
        otp_plain=body.otp,
        password=body.password,
        db=db,
    )
    _set_refresh_cookie(response, refresh_plain)
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email + password",
)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user, access_token, refresh_plain = await service.login_user(
        email=body.email,
        password=body.password,
        db=db,
    )
    _set_refresh_cookie(response, refresh_plain)
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token → new access token",
)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    if not refresh_token:
        raise AuthenticationError(message="No refresh token provided.")

    user, new_access, new_refresh = await service.refresh_access_token(
        refresh_token_plain=refresh_token,
        db=db,
    )
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(
        access_token=new_access,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Revoke refresh token and clear cookie",
)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE),
    db: AsyncSession = Depends(get_db),
) -> LogoutResponse:
    if refresh_token:
        await service.logout_user(refresh_token_plain=refresh_token, db=db)
    _clear_refresh_cookie(response)
    return LogoutResponse(message="Logged out successfully.")


@router.get(
    "/me",
    response_model=UserOut,
    summary="Return the currently authenticated user",
)
async def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)
