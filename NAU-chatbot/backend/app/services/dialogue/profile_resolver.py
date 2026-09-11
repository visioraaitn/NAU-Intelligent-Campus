from __future__ import annotations

from app.domain.conversation.models import AcademicProfile, ConversationState
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
        if facts.denies_bac and subject.profile is AcademicProfile.NEW_BAC:
            subject.profile = AcademicProfile.UNKNOWN
            subject.bac_specialty = None
            subject.bac_average = None
            subject.math_grade = None
            subject.math_comfort = None
        if facts.profile is not None and (
            facts.correction or facts.profile.rank >= subject.profile.rank
        ):
            subject.profile = facts.profile
            if facts.correction:
                subject.pending_slot = None
                subject.asked_slots.clear()
                subject.pending_action = None
                subject.recommended_offer = None
                subject.recommended_specialisation = None
                subject.offer_intro_done = False
                if facts.profile not in {AcademicProfile.LICENCE_STUDENT, AcademicProfile.LICENCE_HOLDER}:
                    subject.licence_specialty = None
                    subject.licence_year = None
                    subject.finishing_current_degree = False
        for field in ("bac_specialty", "bac_average", "math_grade", "licence_year", "target"):
            if facts.denies_bac and field != "target":
                continue
            value = getattr(facts, field)
            if value is not None:
                setattr(subject, field, value)
        if (
            facts.licence_specialty is not None
            and (facts.profile is not None or facts.credential_answer)
            and subject.profile
            in {AcademicProfile.LICENCE_STUDENT, AcademicProfile.LICENCE_HOLDER}
        ):
            subject.licence_specialty = facts.licence_specialty
        if facts.licence_year is not None and subject.profile in {
            AcademicProfile.LICENCE_STUDENT,
            AcademicProfile.LICENCE_HOLDER,
        }:
            subject.licence_year = facts.licence_year
        if facts.math_grade is not None:
            subject.math_comfort = (
                "HIGH" if facts.math_grade >= 14 else "MEDIUM" if facts.math_grade >= 10 else "LOW"
            )
        subject.finishing_current_degree = (
            subject.finishing_current_degree or facts.finishing_current_degree
        )
        subject.pre_registration_completed = (
            subject.pre_registration_completed
            or facts.pre_registration_completed
        )
        subject.last_scope = facts.scope.value
        subject.interests = list(dict.fromkeys((*subject.interests, *facts.interests)))
        subject.rejected_offers = list(
            dict.fromkeys((*subject.rejected_offers, *negation.rejected_offers))
        )
        subject.rejected_domains = list(
            dict.fromkeys((*subject.rejected_domains, *negation.rejected_domains))
        )
