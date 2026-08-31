from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.exceptions import ConflictError
from app.services.memory.lock import SessionLockManager


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_same_session_cannot_be_processed_concurrently(
    fake_redis,
    test_settings,
) -> None:
    manager = SessionLockManager(fake_redis, test_settings)
    session_id = uuid4()
    key = f"{manager.KEY_PREFIX}{session_id}"

    async with manager.lock(session_id, wait_seconds=0.2):
        assert key in fake_redis.values
        with pytest.raises(ConflictError) as error:
            async with manager.lock(session_id, wait_seconds=0.06):
                raise AssertionError("the second owner must never enter")

    assert error.value.status_code == 409
    assert "déjà en cours" in error.value.message
    assert key not in fake_redis.values

    # The lease is released on exit, so a later turn for the same session works.
    async with manager.lock(session_id, wait_seconds=0.2):
        assert key in fake_redis.values


async def test_different_sessions_can_be_processed_in_parallel(
    fake_redis,
    test_settings,
) -> None:
    manager = SessionLockManager(fake_redis, test_settings)
    first = uuid4()
    second = uuid4()

    async with manager.lock(first, wait_seconds=0.2):
        async with manager.lock(second, wait_seconds=0.2):
            assert f"{manager.KEY_PREFIX}{first}" in fake_redis.values
            assert f"{manager.KEY_PREFIX}{second}" in fake_redis.values


async def test_lock_release_is_owner_safe(fake_redis, test_settings) -> None:
    manager = SessionLockManager(fake_redis, test_settings)
    session_id = uuid4()
    key = f"{manager.KEY_PREFIX}{session_id}"

    async with manager.lock(session_id, wait_seconds=0.2):
        original_token = fake_redis.values[key]
        fake_redis.values[key] = "new-owner-token"

    assert original_token != "new-owner-token"
    assert fake_redis.values[key] == "new-owner-token"

