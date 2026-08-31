from __future__ import annotations

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.core.dependencies import require_admin
from app.core.exceptions import AuthenticationError
from app.core.security import AuthService, verify_csrf


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_admin_login_issues_a_scoped_access_and_refresh_pair(
    fake_redis,
    test_settings,
) -> None:
    auth = AuthService(fake_redis, test_settings)

    pair = await auth.login("catalog-admin", "correct-horse-battery-staple")
    access = auth.decode(pair.access_token, expected_type="access")
    refresh = auth.decode(pair.refresh_token, expected_type="refresh")

    assert access["sub"] == "catalog-admin"
    assert access["typ"] == "access"
    assert refresh["sub"] == "catalog-admin"
    assert refresh["typ"] == "refresh"
    assert pair.csrf_token
    assert any(key.startswith(AuthService.REFRESH_PREFIX) for key in fake_redis.values)


async def test_invalid_admin_credentials_are_rejected(fake_redis, test_settings) -> None:
    auth = AuthService(fake_redis, test_settings)

    with pytest.raises(AuthenticationError, match="Identifiants invalides"):
        await auth.login("catalog-admin", "wrong-password")
    with pytest.raises(AuthenticationError, match="Identifiants invalides"):
        await auth.login("unknown-admin", "correct-horse-battery-staple")


async def test_refresh_token_is_rotated_and_cannot_be_replayed(
    fake_redis,
    test_settings,
) -> None:
    auth = AuthService(fake_redis, test_settings)
    original = await auth.login("catalog-admin", "correct-horse-battery-staple")

    rotated = await auth.refresh(original.refresh_token)

    assert rotated.refresh_token != original.refresh_token
    assert auth.decode(rotated.access_token, expected_type="access")["sub"] == "catalog-admin"
    with pytest.raises(AuthenticationError, match="invalide ou révoquée"):
        await auth.refresh(original.refresh_token)


async def test_admin_dependency_accepts_only_a_bearer_access_token(
    fake_redis,
    test_settings,
) -> None:
    auth = AuthService(fake_redis, test_settings)
    pair = await auth.login("catalog-admin", "correct-horse-battery-staple")

    principal = await require_admin(
        credentials=HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=pair.access_token,
        ),
        auth=auth,
    )

    assert principal == "catalog-admin"
    with pytest.raises(AuthenticationError):
        await require_admin(credentials=None, auth=auth)
    with pytest.raises(AuthenticationError, match="Type de jeton invalide"):
        await require_admin(
            credentials=HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=pair.refresh_token,
            ),
            auth=auth,
        )


async def test_csrf_requires_equal_nonempty_cookie_and_header_values() -> None:
    verify_csrf("same-token", "same-token")

    for cookie, header in (
        (None, None),
        ("token", None),
        (None, "token"),
        ("cookie-token", "header-token"),
    ):
        with pytest.raises(AuthenticationError, match="CSRF"):
            verify_csrf(cookie, header)

