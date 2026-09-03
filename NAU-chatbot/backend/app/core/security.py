from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from redis.asyncio import Redis

from app.core.config import Settings
from app.core.exceptions import AuthenticationError


REFRESH_COOKIE = "iit_refresh"
CSRF_COOKIE = "iit_csrf"
AUTH_ISSUER = "iit-academic-assistant"
AUTH_AUDIENCE = "iit-admin"


@dataclass(frozen=True, slots=True)
class AuthPrincipal:
    subject: str
    role: Literal["USER", "ADMIN"]
    name: str
    email: str | None = None
    user_id: UUID | None = None


class UserIdentityStore(Protocol):
    async def get_by_email(self, email: str) -> Any | None: ...
    async def get(self, user_id: UUID) -> Any | None: ...


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    csrf_token: str
    access_expires_in: int
    refresh_expires_in: int
    principal: AuthPrincipal


class AuthService:
    REFRESH_PREFIX = "iit:auth:refresh:"

    def __init__(
        self,
        redis: Redis,
        settings: Settings,
        users: UserIdentityStore | None = None,
    ) -> None:
        self.redis = redis
        self.settings = settings
        self.passwords = PasswordHasher()
        self.users = users
        self._dummy_hash = self.passwords.hash("not-the-configured-password")

    def verify_admin_password(self, username: str, password: str) -> bool:
        configured_username = self.settings.admin_username
        configured_hash = self.settings.admin_password_hash.get_secret_value()
        if not configured_hash or not hmac.compare_digest(username, configured_username):
            # Run a dummy verification-equivalent hash operation to reduce username timing signal.
            try:
                self.passwords.verify(self._dummy_hash, password)
            except VerifyMismatchError:
                pass
            return False
        try:
            return self.passwords.verify(configured_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            return False

    async def login(self, username: str, password: str) -> TokenPair:
        if self.verify_admin_password(username, password):
            return await self._issue(self.admin_principal())
        user = await self.users.get_by_email(username.strip().casefold()) if self.users else None
        if user is None or not getattr(user, "active", False):
            self._verify_dummy(password)
            raise AuthenticationError("Identifiants invalides.")
        try:
            valid = self.passwords.verify(user.password_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            valid = False
        if not valid:
            raise AuthenticationError("Identifiants invalides.")
        return await self._issue(self.user_principal(user))

    async def refresh(self, refresh_token: str) -> TokenPair:
        claims = self.decode(refresh_token, expected_type="refresh")
        try:
            jti = UUID(str(claims["jti"]))
        except (TypeError, ValueError) as exc:
            raise AuthenticationError("Session de renouvellement invalide.") from exc
        key = f"{self.REFRESH_PREFIX}{jti}"
        stored = await self.redis.getdel(key)
        if stored != claims["sub"]:
            raise AuthenticationError("Session de renouvellement invalide ou révoquée.")
        principal = await self.principal_from_claims(claims)
        return await self._issue(principal)

    async def revoke_refresh(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        try:
            claims = self.decode(refresh_token, expected_type="refresh")
        except AuthenticationError:
            return
        await self.redis.delete(f"{self.REFRESH_PREFIX}{claims['jti']}")

    def decode(
        self,
        token: str,
        *,
        expected_type: Literal["access", "refresh"],
    ) -> dict[str, Any]:
        try:
            claims = jwt.decode(
                token,
                self.settings.jwt_secret.get_secret_value(),
                algorithms=[self.settings.jwt_algorithm],
                audience=AUTH_AUDIENCE,
                issuer=AUTH_ISSUER,
                options={"require": ["exp", "iat", "jti", "sub", "typ"]},
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Jeton invalide ou expiré.") from exc
        if claims.get("typ") != expected_type:
            raise AuthenticationError("Type de jeton invalide.")
        role = claims.get("role")
        if role is None and claims.get("sub") == self.settings.admin_username:
            claims["role"] = "ADMIN"
        elif role not in {"USER", "ADMIN"}:
            raise AuthenticationError("Rôle de jeton invalide.")
        if claims["role"] == "ADMIN" and claims.get("sub") != self.settings.admin_username:
            raise AuthenticationError("Identité administrateur invalide.")
        return claims

    async def issue_user(self, user: Any) -> TokenPair:
        return await self._issue(self.user_principal(user))

    async def principal_from_claims(self, claims: dict[str, Any]) -> AuthPrincipal:
        if claims["role"] == "ADMIN":
            return self.admin_principal()
        if self.users is None:
            raise AuthenticationError()
        try:
            user_id = UUID(str(claims["sub"]))
        except (TypeError, ValueError) as exc:
            raise AuthenticationError("Identité utilisateur invalide.") from exc
        user = await self.users.get(user_id)
        if user is None or not user.active or user.role != "USER":
            raise AuthenticationError("Compte utilisateur indisponible.")
        return self.user_principal(user)

    def hash_password(self, password: str) -> str:
        return self.passwords.hash(password)

    def admin_principal(self) -> AuthPrincipal:
        return AuthPrincipal(
            subject=self.settings.admin_username,
            role="ADMIN",
            name="Administrateur",
        )

    @staticmethod
    def user_principal(user: Any) -> AuthPrincipal:
        return AuthPrincipal(
            subject=str(user.id),
            role="USER",
            name=user.name,
            email=user.email,
            user_id=user.id,
        )

    def _verify_dummy(self, password: str) -> None:
        try:
            self.passwords.verify(self._dummy_hash, password)
        except VerifyMismatchError:
            pass

    async def _issue(self, principal: AuthPrincipal) -> TokenPair:
        access_jti = uuid4()
        refresh_jti = uuid4()
        access = self._encode(principal, access_jti, "access", self.settings.jwt_access_ttl)
        refresh = self._encode(principal, refresh_jti, "refresh", self.settings.jwt_refresh_ttl)
        await self.redis.set(
            f"{self.REFRESH_PREFIX}{refresh_jti}",
            principal.subject,
            ex=self.settings.jwt_refresh_ttl,
        )
        return TokenPair(
            access,
            refresh,
            secrets.token_urlsafe(32),
            self.settings.jwt_access_ttl,
            self.settings.jwt_refresh_ttl,
            principal,
        )

    def _encode(
        self,
        principal: AuthPrincipal,
        jti: UUID,
        token_type: Literal["access", "refresh"],
        ttl: int,
    ) -> str:
        now = datetime.now(UTC)
        return jwt.encode(
            {
                "sub": principal.subject,
                "role": principal.role,
                "jti": str(jti),
                "typ": token_type,
                "iss": AUTH_ISSUER,
                "aud": AUTH_AUDIENCE,
                "iat": now,
                "exp": now + timedelta(seconds=ttl),
            },
            self.settings.jwt_secret.get_secret_value(),
            algorithm=self.settings.jwt_algorithm,
        )


def verify_csrf(cookie_value: str | None, header_value: str | None) -> None:
    if not cookie_value or not header_value or not hmac.compare_digest(cookie_value, header_value):
        raise AuthenticationError("Jeton CSRF invalide.")
