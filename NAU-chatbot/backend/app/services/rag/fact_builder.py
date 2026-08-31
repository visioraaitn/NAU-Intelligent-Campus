from __future__ import annotations

from collections.abc import Sequence

from app.domain.rag.schemas import RagFact, RetrievedChunk


class FactBuilder:
    def build(self, chunks: Sequence[RetrievedChunk]) -> tuple[RagFact, ...]:
        facts: list[RagFact] = []
        for chunk in chunks:
            metadata = chunk.metadata
            facts.append(
                RagFact(
                    text=chunk.content,
                    entity_type=str(metadata.get("entity_type", "UNKNOWN")),
                    entity_id=int(metadata.get("entity_id", 0)),
                    formation_code=_optional(metadata.get("formation_code")),
                    specialisation_code=_optional(metadata.get("specialisation_code")),
                    source_ref=_optional(metadata.get("source_ref")),
                    supporting_chunk_id=chunk.id,
                    element_type=_optional(metadata.get("element_type")),
                )
            )
        return tuple(facts)


def _optional(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None
