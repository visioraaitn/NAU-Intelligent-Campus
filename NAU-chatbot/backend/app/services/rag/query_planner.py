from __future__ import annotations

from collections.abc import Sequence

from app.core.file_config import RagFileConfig, rag_config
from app.domain.rag.schemas import RagQueryPlan


INTENT_ENTITY_FILTERS: dict[str, tuple[str | None, str | None]] = {
    "FEES": ("TARIF", None),
    "ACCREDITATION": ("ACCREDITATION", None),
    "ADMISSION": ("ORIENTATION_RULE", None),
    "CAREERS": ("FORMATION_ELEMENT", "METIER"),
    "PROGRAMME": ("FORMATION_ELEMENT", "CONTENU_PROGRAMME"),
    "CERTIFICATIONS": ("FORMATION_ELEMENT", "CERTIFICATION"),
    "INTERNATIONAL": ("FORMATION_ELEMENT", "MOBILITE"),
}


class RagQueryPlanner:
    def __init__(self, config: RagFileConfig | None = None) -> None:
        self.config = config or rag_config()

    def plan(
        self,
        query: str,
        intents: Sequence[str],
        *,
        formation_code: str | None,
        specialisation_code: str | None,
    ) -> RagQueryPlan:
        entity_type: str | None = None
        element_type: str | None = None
        for intent in intents:
            if intent in INTENT_ENTITY_FILTERS:
                entity_type, element_type = INTENT_ENTITY_FILTERS[intent]
                break
        return RagQueryPlan(
            query=query,
            formation_code=formation_code,
            specialisation_code=specialisation_code,
            entity_type=entity_type,
            element_type=element_type,
            candidate_count=self.config.candidate_count,
            result_count=self.config.result_count,
            minimum_rerank_score=self.config.minimum_rerank_score,
        )
