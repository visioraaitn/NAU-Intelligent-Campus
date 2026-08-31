from __future__ import annotations

from app.services.llm.providers import EmbeddingProvider, LLMProvider, RerankerProvider


class ModelRegistry:
    """Central provider registry injected into application services."""

    def __init__(
        self,
        llm: LLMProvider,
        embedding: EmbeddingProvider,
        reranker: RerankerProvider,
    ) -> None:
        self.llm = llm
        self.embedding = embedding
        self.reranker = reranker

