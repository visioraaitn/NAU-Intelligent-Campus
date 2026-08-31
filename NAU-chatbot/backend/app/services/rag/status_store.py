from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

from app.core.config import Settings
from app.domain.academic.events import AcademicEntityChanged


class RagJobState(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    RETRYING = "RETRYING"
    FAILED = "FAILED"


class RagStatusStore:
    PREFIX = "iit:rag:status:"
    RECENT_KEY = "iit:rag:recent"

    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.ttl = settings.rag_status_ttl_seconds

    async def enqueue(self, event: AcademicEntityChanged, queue_key: str) -> None:
        """Atomically expose QUEUED status and append the event to its Redis queue."""

        now = datetime.now(UTC)
        payload: dict[str, Any] = event.to_payload()
        payload.update(state=RagJobState.QUEUED.value, updated_at=now.isoformat())
        serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        key = f"{self.PREFIX}{event.event_id}"
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.set(key, serialized, ex=self.ttl)
            pipe.zadd(self.RECENT_KEY, {str(event.event_id): now.timestamp()})
            pipe.zremrangebyrank(self.RECENT_KEY, 0, -501)
            pipe.expire(self.RECENT_KEY, self.ttl)
            pipe.lpush(
                queue_key,
                json.dumps(
                    event.to_payload(),
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            )
            await pipe.execute()

    async def set(
        self,
        event: AcademicEntityChanged,
        state: RagJobState,
        *,
        detail: str | None = None,
    ) -> None:
        now = datetime.now(UTC)
        payload: dict[str, Any] = event.to_payload()
        payload.update(state=state.value, updated_at=now.isoformat())
        if detail:
            payload["detail"] = detail[:500]
        key = f"{self.PREFIX}{event.event_id}"
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.set(key, json.dumps(payload, ensure_ascii=False), ex=self.ttl)
            pipe.zadd(self.RECENT_KEY, {str(event.event_id): now.timestamp()})
            pipe.zremrangebyrank(self.RECENT_KEY, 0, -501)
            pipe.expire(self.RECENT_KEY, self.ttl)
            await pipe.execute()

    async def get(self, event_id: UUID) -> dict[str, Any] | None:
        raw = await self.redis.get(f"{self.PREFIX}{event_id}")
        return json.loads(raw) if raw else None

    async def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        ids = await self.redis.zrevrange(self.RECENT_KEY, 0, max(0, min(limit, 100) - 1))
        if not ids:
            return []
        values = await self.redis.mget([f"{self.PREFIX}{item}" for item in ids])
        return [json.loads(value) for value in values if value]
