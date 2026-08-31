from __future__ import annotations

from typing import Any, Protocol, Sequence, runtime_checkable

from app.domain.rag.schemas import RagDocument, RetrievedChunk


@runtime_checkable
class ChromaRepository(Protocol):
    async def ids_where(self, where: dict[str, Any] | None = None) -> list[str]: ...

    async def existing_hashes(self, ids: Sequence[str]) -> dict[str, str]: ...

    async def upsert(
        self,
        documents: Sequence[RagDocument],
        embeddings: Sequence[Sequence[float]],
    ) -> None: ...

    async def delete_ids(self, ids: Sequence[str]) -> None: ...

    async def delete_where(self, where: dict[str, Any]) -> None: ...

    async def query(
        self,
        embedding: Sequence[float],
        *,
        where: dict[str, Any] | None,
        limit: int,
    ) -> list[RetrievedChunk]: ...

    async def heartbeat(self) -> bool: ...
