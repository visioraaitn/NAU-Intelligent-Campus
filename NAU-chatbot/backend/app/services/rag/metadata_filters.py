from __future__ import annotations

from typing import Any

from app.domain.rag.schemas import RagQueryPlan


class MetadataFilterBuilder:
    @staticmethod
    def build(plan: RagQueryPlan) -> dict[str, Any]:
        clauses: list[dict[str, Any]] = [{"active": {"$eq": True}}]
        for field, value in (
            ("formation_code", plan.formation_code),
            ("entity_type", plan.entity_type),
            ("element_type", plan.element_type),
        ):
            if value:
                clauses.append({field: {"$eq": value}})
        if plan.specialisation_code:
            clauses.append(
                {
                    "$or": [
                        {
                            "specialisation_code": {
                                "$eq": plan.specialisation_code
                            }
                        },
                        {"specialisation_code": {"$eq": ""}},
                    ]
                }
            )
        return clauses[0] if len(clauses) == 1 else {"$and": clauses}
