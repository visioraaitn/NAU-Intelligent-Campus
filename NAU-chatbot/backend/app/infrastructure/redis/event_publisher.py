from __future__ import annotations

from redis.asyncio import Redis

from app.core.config import Settings
from app.domain.academic.events import AcademicEntityChanged, EventPublisher
from app.services.rag.status_store import RagStatusStore


class RedisAcademicEventPublisher(EventPublisher):
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.queue_key = settings.rag_queue_key
        self.status = RagStatusStore(redis, settings)

    async def publish(self, event: AcademicEntityChanged) -> None:
        await self.status.enqueue(event, self.queue_key)
