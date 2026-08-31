from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EligibilityStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class RuleEvidence:
    rule_id: int
    rule_code: str
    source_ref: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class EligibilityDecision:
    status: EligibilityStatus
    formation_id: int
    formation_code: str
    specialisation_id: int | None = None
    specialisation_code: str | None = None
    matched_rules: tuple[RuleEvidence, ...] = ()
    failed_rules: tuple[RuleEvidence, ...] = ()
    unknown_reasons: tuple[str, ...] = ()

    @property
    def source_refs(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                item.source_ref
                for item in (*self.matched_rules, *self.failed_rules)
                if item.source_ref
            )
        )


@dataclass(frozen=True, slots=True)
class RecommendationOption:
    formation_id: int
    formation_code: str
    formation_name: str
    specialisation_id: int | None
    specialisation_code: str | None
    specialisation_name: str | None
    score: float
    eligibility: EligibilityDecision
    supporting_entity_ids: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class RecommendationDecision:
    primary: RecommendationOption | None
    secondary: RecommendationOption | None
    reasoning: tuple[str, ...] = ()
    challenge: str | None = None
    provisional: bool = False
    alternatives: tuple[RecommendationOption, ...] = ()
