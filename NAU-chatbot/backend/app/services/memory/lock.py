from __future__ import annotations

import asyncio
import secrets
from contextlib import asynccontextmanager, suppress
from collections.abc import AsyncIterator
from uuid import UUID

from redis.asyncio import Redis

from app.core.config import Settings
from app.core.exceptions import ConflictError


RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""

EXTEND_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('expire', KEYS[1], ARGV[2])
end
return 0
"""


class SessionLockManager:
    KEY_PREFIX = "iit:lock:session:"

    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.lease_seconds = settings.session_lock_ttl_seconds

    @asynccontextmanager
    async def lock(
        self,
        session_id: UUID,
        *,
        wait_seconds: float = 5.0,
    ) -> AsyncIterator[None]:
        key = f"{self.KEY_PREFIX}{session_id}"
        token = secrets.token_urlsafe(32)
        loop = asyncio.get_running_loop()
        deadline = loop.time() + wait_seconds
        acquired = False
        while loop.time() < deadline:
            acquired = bool(
                await self.redis.set(key, token, ex=self.lease_seconds, nx=True)
            )
            if acquired:
                break
            await asyncio.sleep(0.05)
        if not acquired:
            raise ConflictError(
                "Une autre réponse est déjà en cours pour cette conversation."
            )

        stop = asyncio.Event()
        renewer = asyncio.create_task(self._renew(key, token, stop))
        try:
            yield
        finally:
            stop.set()
            renewer.cancel()
            with suppress(asyncio.CancelledError):
                await renewer
            await self.redis.eval(RELEASE_SCRIPT, 1, key, token)

    async def _renew(self, key: str, token: str, stop: asyncio.Event) -> None:
        interval = max(1.0, self.lease_seconds / 3)
        while not stop.is_set():
            try:
                await asyncio.wait_for(stop.wait(), timeout=interval)
            except TimeoutError:
                extended = await self.redis.eval(
                    EXTEND_SCRIPT,
                    1,
                    key,
                    token,
                    self.lease_seconds,
                )
                if not extended:
                    return

