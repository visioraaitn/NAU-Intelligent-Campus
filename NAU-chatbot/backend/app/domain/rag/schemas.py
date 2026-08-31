from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


Scalar = str | int | float | bool


@dataclass(frozen=True, slots=True)
class RagDocument:
    id: str
    content: str
    metadata: dict[str, Scalar]

    @property
    def content_hash(self) -> str:
        return str(self.metadata["content_hash"])


@dataclass(frozen=True, slots=True)
class RagQueryPlan:
    query: str
    formation_code: str | None = None
    specialisation_code: str | None = None
    entity_type: str | None = None
    element_type: str | None = None
    candidate_count: int = 24
    result_count: int = 6
    minimum_rerank_score: float = -10.0


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    id: str
    content: str
    metadata: dict[str, Any]
    dense_score: float
    rerank_score: float | None = None


@dataclass(frozen=True, slots=True)
class RagFact:
    text: str
    entity_type: str
    entity_id: int
    formation_code: str | None
    specialisation_code: str | None
    source_ref: str | None
    supporting_chunk_id: str
    element_type: str | None = None


@dataclass(frozen=True, slots=True)
class RagResult:
    plan: RagQueryPlan
    chunks: tuple[RetrievedChunk, ...] = field(default_factory=tuple)
    facts: tuple[RagFact, ...] = field(default_factory=tuple)
