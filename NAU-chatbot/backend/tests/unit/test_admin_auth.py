from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.core.dependencies import require_admin, require_user
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import AuthService, verify_csrf


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeUserStore:
    def __init__(self, user) -> None:
        self.user = user

    async def get_by_email(self, email: str):
        return self.user if email == self.user.email else None

    async def get(self, user_id):
        return self.user if user_id == self.user.id else None


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


async def test_user_login_uses_existing_hashing_and_carries_user_role(
    fake_redis,
    test_settings,
) -> None:
    user = SimpleNamespace(
        id=uuid4(),
        name="Ahmed Test",
        email="ahmed@example.com",
        password_hash=AuthService(fake_redis, test_settings).hash_password("user-password"),
        role="USER",
        active=True,
    )
    auth = AuthService(fake_redis, test_settings, FakeUserStore(user))

    pair = await auth.login("AHMED@EXAMPLE.COM", "user-password")
    claims = auth.decode(pair.access_token, expected_type="access")
    principal = await auth.principal_from_claims(claims)
    rotated = await auth.refresh(pair.refresh_token)
    rotated_principal = await auth.principal_from_claims(
        auth.decode(rotated.access_token, expected_type="access")
    )

    assert claims["role"] == "USER"
    assert principal.user_id == user.id
    assert principal.email == user.email
    assert rotated_principal.user_id == user.id
    assert await require_user(principal=principal) == principal

    with pytest.raises(AuthorizationError):
        await require_admin(
            credentials=HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=pair.access_token,
            ),
            auth=auth,
        )


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
