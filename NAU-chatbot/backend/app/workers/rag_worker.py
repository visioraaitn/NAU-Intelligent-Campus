from __future__ import annotations

import asyncio
import json
import logging

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.domain.academic.events import AcademicEntityChanged
from app.infrastructure.chroma import AsyncChromaRepository
from app.infrastructure.db import close_database, get_session_factory
from app.infrastructure.inference.client import HttpInferenceClient
from app.infrastructure.redis import close_redis, get_redis
from app.services.academic.catalog_service import AcademicCatalogService
from app.services.rag.indexer import RagIndexer
from app.services.rag.status_store import RagJobState, RagStatusStore
from app.services.rag.sync_service import RagSyncService


logger = logging.getLogger(__name__)


class RagWorker:
    def __init__(self) -> None:
        self.settings = get_settings()
        configure_logging(self.settings)
        self.redis = get_redis()
        self.status = RagStatusStore(self.redis, self.settings)
        self.chroma = AsyncChromaRepository(self.settings)
        self.inference = HttpInferenceClient(self.settings)
        self.session_factory = get_session_factory()

    async def run_forever(self) -> None:
        await self._recover_interrupted_jobs()
        while True:
            raw = await self.redis.brpoplpush(
                self.settings.rag_queue_key,
                self.settings.rag_processing_key,
                timeout=5,
            )
            if raw is None:
                continue
            await self._handle(raw)

    async def _recover_interrupted_jobs(self) -> None:
        """Return unacknowledged work left by a previous single worker process."""

        recovered = 0
        while True:
            raw = await self.redis.rpoplpush(
                self.settings.rag_processing_key,
                self.settings.rag_queue_key,
            )
            if raw is None:
                break
            recovered += 1
        if recovered:
            logger.warning(
                "RAG_RECOVERED_JOBS",
                extra={"event_fields": {"count": recovered}},
            )

    async def _ack(self, raw: str) -> None:
        await self.redis.lrem(self.settings.rag_processing_key, 1, raw)

    async def _retry(self, raw: str, event: AcademicEntityChanged) -> None:
        delay = min(
            60.0,
            self.settings.rag_retry_base_seconds * (2 ** max(0, event.attempt - 1)),
        )
        await asyncio.sleep(delay)
        payload = json.dumps(event.to_payload(), ensure_ascii=False)
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.lrem(self.settings.rag_processing_key, 1, raw)
            pipe.lpush(self.settings.rag_queue_key, payload)
            await pipe.execute()

    async def _dead_letter(self, raw: str) -> None:
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.lrem(self.settings.rag_processing_key, 1, raw)
            pipe.lpush(self.settings.rag_dead_letter_key, raw)
            await pipe.execute()

    async def _handle(self, raw: str) -> None:
        event: AcademicEntityChanged | None = None
        try:
            event = AcademicEntityChanged.from_payload(json.loads(raw))
            await self.status.set(event, RagJobState.RUNNING)
            async with self.session_factory() as session:
                service = RagSyncService(
                    AcademicCatalogService(session),
                    RagIndexer(self.chroma, self.inference),
                    self.chroma,
                )
                result = await service.process(event)
            await self.status.set(
                event,
                RagJobState.SUCCEEDED,
                detail=(
                    f"upserted={result.upserted}; skipped={result.skipped}; "
                    f"deleted={result.deleted}"
                ),
            )
            await self._ack(raw)
            logger.info("RAG_REINDEX", extra={"event_id": str(event.event_id)})
        except Exception as exc:
            logger.exception("RAG_REINDEX failed")
            if event is None:
                await self._dead_letter(raw)
                return
            retry = event.for_retry()
            if retry.attempt < self.settings.rag_max_attempts:
                await self.status.set(retry, RagJobState.RETRYING, detail=type(exc).__name__)
                await self._retry(raw, retry)
            else:
                await self.status.set(event, RagJobState.FAILED, detail=type(exc).__name__)
                await self._dead_letter(raw)


async def async_main() -> None:
    worker = RagWorker()
    try:
        await worker.run_forever()
    finally:
        await worker.inference.close()
        await close_database()
        await close_redis()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
