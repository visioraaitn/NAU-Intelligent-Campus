from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Header, Request, Response

from app.core.config import Settings
from app.core.dependencies import (
    auth_service,
    client_bucket,
    rate_limiter,
    settings_dependency,
)
from app.core.security import (
    CSRF_COOKIE,
    REFRESH_COOKIE,
    AuthService,
    TokenPair,
    verify_csrf,
)
from app.models.schemas.auth import LoginRequest, LogoutResponse, TokenResponse
from app.services.memory.rate_limiter import RedisRateLimiter


router = APIRouter(prefix="/auth", tags=["auth"])


def _set_cookies(response: Response, pair: TokenPair, settings: Settings) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        pair.refresh_token,
        max_age=pair.refresh_expires_in,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="strict",
        path=f"{settings.api_v1_prefix}/auth",
    )
    response.set_cookie(
        CSRF_COOKIE,
        pair.csrf_token,
        max_age=pair.refresh_expires_in,
        httponly=False,
        secure=settings.secure_cookies,
        samesite="strict",
        path="/",
    )


def _response(pair: TokenPair) -> TokenResponse:
    return TokenResponse(
        access_token=pair.access_token,
        expires_in=pair.access_expires_in,
        csrf_token=pair.csrf_token,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    auth: AuthService = Depends(auth_service),
    limiter: RedisRateLimiter = Depends(rate_limiter),
    settings: Settings = Depends(settings_dependency),
) -> TokenResponse:
    await limiter.enforce(client_bucket(request, "auth-login", settings), 10, 60)
    pair = await auth.login(payload.username, payload.password)
    _set_cookies(response, pair, settings)
    return _response(pair)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    request: Request,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
    auth: AuthService = Depends(auth_service),
    limiter: RedisRateLimiter = Depends(rate_limiter),
    settings: Settings = Depends(settings_dependency),
) -> TokenResponse:
    await limiter.enforce(client_bucket(request, "auth-refresh", settings), 20, 60)
    verify_csrf(csrf_cookie, csrf_header)
    if not refresh_token:
        from app.core.exceptions import AuthenticationError

        raise AuthenticationError()
    pair = await auth.refresh(refresh_token)
    _set_cookies(response, pair, settings)
    return _response(pair)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    request: Request,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
    auth: AuthService = Depends(auth_service),
    limiter: RedisRateLimiter = Depends(rate_limiter),
    settings: Settings = Depends(settings_dependency),
) -> LogoutResponse:
    await limiter.enforce(client_bucket(request, "auth-logout", settings), 30, 60)
    verify_csrf(csrf_cookie, csrf_header)
    await auth.revoke_refresh(refresh_token)
    response.delete_cookie(REFRESH_COOKIE, path=f"{settings.api_v1_prefix}/auth")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return LogoutResponse()
