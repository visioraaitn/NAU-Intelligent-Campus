from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

import chromadb

from app.core.config import Settings
from app.domain.rag.schemas import RagDocument, RetrievedChunk


class AsyncChromaRepository:
    """Async boundary around Chroma's synchronous HTTP client."""

    def __init__(self, settings: Settings) -> None:
        self._host = settings.chroma_host
        self._port = settings.chroma_port
        self._client: Any | None = None
        self._client_lock = asyncio.Lock()
        self._collection_name = settings.chroma_collection
        self._collection: Any | None = None
        self._collection_lock = asyncio.Lock()

    async def _get_client(self) -> Any:
        if self._client is None:
            async with self._client_lock:
                if self._client is None:
                    self._client = await asyncio.to_thread(
                        chromadb.HttpClient,
                        host=self._host,
                        port=self._port,
                    )
        return self._client

    async def _get_collection(self) -> Any:
        if self._collection is None:
            async with self._collection_lock:
                if self._collection is None:
                    client = await self._get_client()
                    self._collection = await asyncio.to_thread(
                        client.get_or_create_collection,
                        name=self._collection_name,
                        metadata={"hnsw:space": "cosine"},
                    )
        return self._collection

    async def ids_where(self, where: dict[str, Any] | None = None) -> list[str]:
        collection = await self._get_collection()
        kwargs: dict[str, Any] = {"include": ["metadatas"]}
        if where:
            kwargs["where"] = where
        result = await asyncio.to_thread(collection.get, **kwargs)
        return [str(item_id) for item_id in result.get("ids", [])]

    async def existing_hashes(self, ids: Sequence[str]) -> dict[str, str]:
        if not ids:
            return {}
        collection = await self._get_collection()
        result = await asyncio.to_thread(collection.get, ids=list(ids), include=["metadatas"])
        return {
            str(item_id): str(metadata.get("content_hash", ""))
            for item_id, metadata in zip(
                result.get("ids", []), result.get("metadatas", []), strict=False
            )
            if metadata
        }

    async def upsert(
        self,
        documents: Sequence[RagDocument],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        if not documents:
            return
        collection = await self._get_collection()
        await asyncio.to_thread(
            collection.upsert,
            ids=[doc.id for doc in documents],
            documents=[doc.content for doc in documents],
            metadatas=[doc.metadata for doc in documents],
            embeddings=[list(vector) for vector in embeddings],
        )

    async def delete_ids(self, ids: Sequence[str]) -> None:
        if ids:
            collection = await self._get_collection()
            await asyncio.to_thread(collection.delete, ids=list(ids))

    async def delete_where(self, where: dict[str, Any]) -> None:
        collection = await self._get_collection()
        await asyncio.to_thread(collection.delete, where=where)

    async def query(
        self,
        embedding: Sequence[float],
        *,
        where: dict[str, Any] | None,
        limit: int,
    ) -> list[RetrievedChunk]:
        collection = await self._get_collection()
        kwargs: dict[str, Any] = {
            "query_embeddings": [list(embedding)],
            "n_results": limit,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where
        result = await asyncio.to_thread(collection.query, **kwargs)
        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadata = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        return [
            RetrievedChunk(
                id=str(item_id),
                content=str(content),
                metadata=dict(meta or {}),
                dense_score=1.0 - float(distance),
            )
            for item_id, content, meta, distance in zip(
                ids, documents, metadata, distances, strict=False
            )
        ]

    async def heartbeat(self) -> bool:
        client = await self._get_client()
        await asyncio.to_thread(client.heartbeat)
        return True
