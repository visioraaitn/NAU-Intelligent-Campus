from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from argon2 import PasswordHasher


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Make configuration deterministic before any application module is imported.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_SECRET_KEY", "test-app-secret-key")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key")
os.environ.setdefault("POSTGRES_PASSWORD", "test-postgres-password")
os.environ.setdefault("INFERENCE_SERVICE_TOKEN", "test-inference-token")

from app.core.config import Settings  # noqa: E402
from app.repositories.academic import Page, PageRequest  # noqa: E402


class FakeRepository:
    """Small active-by-default repository double matching the academic API."""

    def __init__(self, items: list[Any] | tuple[Any, ...] = ()) -> None:
        self.items = list(items)
        self.list_requests: list[PageRequest] = []

    async def list(self, request: PageRequest | None = None) -> Page[Any]:
        query = request or PageRequest()
        self.list_requests.append(query)
        items = [
            item
            for item in self.items
            if query.include_inactive or getattr(item, "actif", True)
        ]
        for field, expected in query.filters.items():
            if isinstance(expected, (list, tuple, set, frozenset)):
                items = [item for item in items if getattr(item, field, None) in expected]
            else:
                items = [item for item in items if getattr(item, field, None) == expected]
        start = query.offset
        return Page(items[start : start + query.page_size], len(items), query.page, query.page_size)

    async def get(
        self,
        entity_id: int | None,
        *,
        include_inactive: bool = False,
        for_update: bool = False,
    ) -> Any | None:
        del for_update
        return next(
            (
                item
                for item in self.items
                if getattr(item, "id", None) == entity_id
                and (include_inactive or getattr(item, "actif", True))
            ),
            None,
        )

    async def require(
        self,
        entity_id: int,
        *,
        include_inactive: bool = False,
        for_update: bool = False,
    ) -> Any:
        item = await self.get(
            entity_id,
            include_inactive=include_inactive,
            for_update=for_update,
        )
        if item is None:
            raise LookupError(entity_id)
        return item

    async def get_by_code(
        self,
        code: str | None,
        *,
        include_inactive: bool = False,
    ) -> Any | None:
        return next(
            (
                item
                for item in self.items
                if getattr(item, "code", None) == code
                and (include_inactive or getattr(item, "actif", True))
            ),
            None,
        )


class FakeRedis:
    """Redis subset used by authentication and the per-session lease tests."""

    def __init__(self) -> None:
        self.values: dict[str, Any] = {}
        self.set_calls: list[tuple[str, Any, int | None, bool]] = []
        self.eval_calls: list[tuple[str, tuple[Any, ...]]] = []

    async def set(
        self,
        key: str,
        value: Any,
        *,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool:
        self.set_calls.append((key, value, ex, nx))
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    async def get(self, key: str) -> Any | None:
        return self.values.get(key)

    async def getdel(self, key: str) -> Any | None:
        return self.values.pop(key, None)

    async def delete(self, key: str) -> int:
        existed = key in self.values
        self.values.pop(key, None)
        return int(existed)

    async def eval(self, script: str, number_of_keys: int, *args: Any) -> int:
        assert number_of_keys == 1
        self.eval_calls.append((script, args))
        key, token, *rest = args
        if self.values.get(key) != token:
            return 0
        if "expire" in script.lower():
            assert rest
            return 1
        self.values.pop(key, None)
        return 1


@pytest.fixture(scope="session")
def admin_password_hash() -> str:
    # Reduced test-only cost; the resulting Argon2 hash is compatible with the
    # production verifier and avoids embedding a plaintext credential in config.
    return PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1).hash(
        "correct-horse-battery-staple"
    )


@pytest.fixture
def test_settings(admin_password_hash: str) -> Settings:
    return Settings(
        app_env="test",
        app_secret_key="test-app-secret-key",
        postgres_password="test-postgres-password",
        redis_url="redis://unused:6379/15",
        inference_service_token="test-inference-token",
        admin_username="catalog-admin",
        admin_password_hash=admin_password_hash,
        jwt_secret="test-jwt-secret-key",
        jwt_access_ttl=60,
        jwt_refresh_ttl=900,
        session_lock_ttl_seconds=15,
        secure_cookies=False,
    )


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def repository_factory():
    def factory(items: list[Any] | tuple[Any, ...] = ()) -> FakeRepository:
        return FakeRepository(items)

    return factory

