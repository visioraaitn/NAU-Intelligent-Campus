from __future__ import annotations

import asyncio
from collections.abc import Sequence

from app.core.file_config import ModelsConfig, models_config
from app.infrastructure.inference.huggingface import (
    HuggingFaceEmbedding,
    HuggingFaceLLM,
    HuggingFaceReranker,
)
from app.services.llm.providers import LLMMessage


class ModelManager:
    """Own each heavy model once and enforce independent concurrency budgets."""

    def __init__(self, config: ModelsConfig | None = None) -> None:
        self.config = config or models_config()
        self.esprit: HuggingFaceLLM | None = None
        self.final: HuggingFaceLLM | None = None
        self.embedding: HuggingFaceEmbedding | None = None
        self.reranker: HuggingFaceReranker | None = None
        self._locks = {
            "esprit": asyncio.Semaphore(self.config.esprit.max_concurrency),
            "final": asyncio.Semaphore(self.config.final.max_concurrency),
            "embedding": asyncio.Semaphore(self.config.embedding.max_concurrency),
            "reranker": asyncio.Semaphore(self.config.reranker.max_concurrency),
        }

    async def load(self) -> None:
        if any(item.provider != "huggingface" for item in (self.config.esprit, self.config.final, self.config.embedding, self.config.reranker)):
            raise NotImplementedError("Configure the future vLLM adapter before selecting it")
        # Load GPU models sequentially to avoid transient duplicate VRAM pressure.
        self.esprit = await asyncio.to_thread(
            HuggingFaceLLM, self.config.esprit, allow_adapter=True
        )
        self.final = await asyncio.to_thread(
            HuggingFaceLLM, self.config.final, allow_adapter=False
        )
        self.embedding, self.reranker = await asyncio.gather(
            asyncio.to_thread(HuggingFaceEmbedding, self.config.embedding),
            asyncio.to_thread(HuggingFaceReranker, self.config.reranker),
        )

    @property
    def ready(self) -> bool:
        return all((self.esprit, self.final, self.embedding, self.reranker))

    async def generate(self, role: str, messages: Sequence[LLMMessage], max_new_tokens: int) -> str:
        model = self.esprit if role == "esprit" else self.final if role == "final" else None
        if model is None:
            raise RuntimeError(f"model role {role!r} is unavailable")
        async with self._locks[role]:
            return await asyncio.to_thread(model.generate, messages, max_new_tokens)

    async def embed(
        self,
        texts: Sequence[str],
        *,
        query: bool = False,
    ) -> list[list[float]]:
        if self.embedding is None:
            raise RuntimeError("embedding model unavailable")
        async with self._locks["embedding"]:
            return await asyncio.to_thread(self.embedding.embed, texts, query=query)

    async def rerank(self, query: str, documents: Sequence[str]) -> list[float]:
        if self.reranker is None:
            raise RuntimeError("reranker unavailable")
        async with self._locks["reranker"]:
            return await asyncio.to_thread(self.reranker.rerank, query, documents)
