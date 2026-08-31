from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.infrastructure.db import close_database, get_session_factory
from app.infrastructure.redis import close_redis, get_redis
from app.infrastructure.redis.event_publisher import RedisAcademicEventPublisher
from app.repositories.academic import FormationRepository
from app.services.admin.rag_service import RagAdminService
from app.services.rag.status_store import RagStatusStore


async def enqueue_full_reindex() -> int:
    settings = get_settings()
    redis = get_redis()
    publisher = RedisAcademicEventPublisher(redis, settings)
    async with get_session_factory()() as session:
        result = await RagAdminService(
            FormationRepository(session),
            publisher,
            RagStatusStore(redis, settings),
        ).enqueue_all()
    return result.queued


async def async_main() -> None:
    try:
        count = await enqueue_full_reindex()
        print(f"Queued {count} catalogue reconciliation job(s)")
    finally:
        await close_database()
        await close_redis()


if __name__ == "__main__":
    asyncio.run(async_main())
