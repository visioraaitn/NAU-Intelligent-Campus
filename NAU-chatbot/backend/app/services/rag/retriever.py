from __future__ import annotations

from app.domain.rag.schemas import RagQueryPlan, RagResult, RetrievedChunk
from app.repositories.chroma import ChromaRepository
from app.services.llm.providers import EmbeddingProvider, RerankerProvider
from app.services.rag.fact_builder import FactBuilder
from app.services.rag.metadata_filters import MetadataFilterBuilder


class RagRetriever:
    def __init__(
        self,
        repository: ChromaRepository,
        embeddings: EmbeddingProvider,
        reranker: RerankerProvider,
    ) -> None:
        self.repository = repository
        self.embeddings = embeddings
        self.reranker = reranker
        self.fact_builder = FactBuilder()

    async def retrieve(self, plan: RagQueryPlan) -> RagResult:
        vectors = await self.embeddings.embed([plan.query], query=True)
        if not vectors:
            return RagResult(plan=plan)
        candidates = await self.repository.query(
            vectors[0],
            where=MetadataFilterBuilder.build(plan),
            limit=plan.candidate_count,
        )
        if not candidates:
            return RagResult(plan=plan)
        scores = await self.reranker.rerank(
            plan.query,
            [candidate.content for candidate in candidates],
        )
        if len(scores) != len(candidates):
            raise RuntimeError("reranker provider returned an unexpected score count")
        ranked = sorted(
            (
                RetrievedChunk(
                    id=item.id,
                    content=item.content,
                    metadata=item.metadata,
                    dense_score=item.dense_score,
                    rerank_score=float(score),
                )
                for item, score in zip(candidates, scores, strict=False)
                if float(score) >= plan.minimum_rerank_score
            ),
            key=lambda item: (
                item.rerank_score
                if item.rerank_score is not None
                else float("-inf")
            ),
            reverse=True,
        )[: plan.result_count]
        return RagResult(
            plan=plan,
            chunks=tuple(ranked),
            facts=self.fact_builder.build(ranked),
        )
