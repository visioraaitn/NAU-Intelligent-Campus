from __future__ import annotations

from app.domain.conversation.models import ConversationState
from app.services.dialogue.negation_detector import NegationResult
from app.services.dialogue.raw_fact_extractor import RawFacts


class ProfileResolver:
    def apply(
        self,
        state: ConversationState,
        facts: RawFacts,
        negation: NegationResult,
    ) -> None:
        state.active_subject = facts.subject
        subject = state.active_state
        if facts.profile is not None and (
            facts.correction or facts.profile.rank >= subject.profile.rank
        ):
            subject.profile = facts.profile
        for field in ("bac_specialty", "bac_average", "math_grade", "licence_specialty", "target"):
            value = getattr(facts, field)
            if value is not None:
                setattr(subject, field, value)
        if facts.math_grade is not None:
            subject.math_comfort = (
                "HIGH" if facts.math_grade >= 14 else "MEDIUM" if facts.math_grade >= 10 else "LOW"
            )
        subject.finishing_current_degree = (
            subject.finishing_current_degree or facts.finishing_current_degree
        )
        subject.last_scope = facts.scope.value
        subject.interests = list(dict.fromkeys((*subject.interests, *facts.interests)))
        subject.rejected_offers = list(
            dict.fromkeys((*subject.rejected_offers, *negation.rejected_offers))
        )
        subject.rejected_domains = list(
            dict.fromkeys((*subject.rejected_domains, *negation.rejected_domains))
        )

