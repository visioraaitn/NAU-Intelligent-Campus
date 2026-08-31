from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import TypeVar

from app.core.file_config import RagFileConfig, rag_config
from app.domain.rag.schemas import RagDocument
from app.repositories.chroma import ChromaRepository
from app.services.llm.providers import EmbeddingProvider


@dataclass(frozen=True, slots=True)
class IndexResult:
    considered: int
    upserted: int
    skipped: int
    deleted: int


class RagIndexer:
    def __init__(
        self,
        repository: ChromaRepository,
        embeddings: EmbeddingProvider,
        config: RagFileConfig | None = None,
    ) -> None:
        self.repository = repository
        self.embeddings = embeddings
        self.batch_size = (config or rag_config()).index_batch_size

    async def index(self, documents: Sequence[RagDocument]) -> IndexResult:
        inactive = [doc.id for doc in documents if not bool(doc.metadata.get("active"))]
        active = [doc for doc in documents if bool(doc.metadata.get("active"))]
        existing: dict[str, str] = {}
        for batch in _batches(active, self.batch_size):
            existing.update(
                await self.repository.existing_hashes([doc.id for doc in batch])
            )
        changed = [doc for doc in active if existing.get(doc.id) != doc.content_hash]
        for batch in _batches(changed, self.batch_size):
            vectors = await self.embeddings.embed([doc.content for doc in batch])
            if len(vectors) != len(batch):
                raise RuntimeError("embedding provider returned an unexpected vector count")
            await self.repository.upsert(batch, vectors)
        for batch in _batches(inactive, self.batch_size):
            await self.repository.delete_ids(batch)
        return IndexResult(len(documents), len(changed), len(active) - len(changed), len(inactive))

    async def reconcile(
        self,
        documents: Sequence[RagDocument],
        *,
        where: dict[str, object] | None = None,
    ) -> IndexResult:
        desired_ids = {
            document.id
            for document in documents
            if bool(document.metadata.get("active"))
        }
        existing_ids = set(await self.repository.ids_where(where))
        stale_ids = sorted(existing_ids.difference(desired_ids))
        result = await self.index(documents)
        for batch in _batches(stale_ids, self.batch_size):
            await self.repository.delete_ids(batch)
        return IndexResult(
            considered=result.considered,
            upserted=result.upserted,
            skipped=result.skipped,
            deleted=result.deleted + len(stale_ids),
        )


BatchItem = TypeVar("BatchItem")


def _batches(items: Sequence[BatchItem], size: int) -> Iterator[Sequence[BatchItem]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]
