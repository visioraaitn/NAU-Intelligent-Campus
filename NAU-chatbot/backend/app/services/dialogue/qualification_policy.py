from __future__ import annotations

from collections.abc import Sequence

from app.domain.conversation.models import AcademicProfile, SubjectState


QUESTIONS = {
    "PROFILE": "Dis-moi simplement où tu en es actuellement : bac, licence, prépa ou autre ?",
    "BAC_SPECIALTY": "Quelle est ta section de bac ?",
    "BAC_LEVEL": "Tu peux me donner ta moyenne au bac et ta note en maths, par exemple « 10 w 9 » ?",
    "LICENCE_SPECIALTY": "Quelle est ta spécialité de licence ?",
    "INTEREST": "Qu'est-ce qui t'attire le plus : logiciel/Data-IA, cyber-réseaux, IoT, industrie ou un autre domaine ?",
}


class QualificationPolicy:
    def choose(self, subject: SubjectState, intents: Sequence[str]) -> str | None:
        if "ORIENTATION" not in intents:
            return None
        if subject.profile is AcademicProfile.UNKNOWN:
            return "PROFILE"
        if subject.profile is AcademicProfile.NEW_BAC and not subject.bac_specialty:
            return "BAC_SPECIALTY"
        if subject.profile in {AcademicProfile.LICENCE_STUDENT, AcademicProfile.LICENCE_HOLDER} and not subject.licence_specialty:
            return "LICENCE_SPECIALTY"
        if subject.profile in {AcademicProfile.LICENCE_STUDENT, AcademicProfile.LICENCE_HOLDER} and subject.licence_specialty:
            return None
        if subject.profile is not AcademicProfile.NEW_BAC and not subject.interests:
            return "INTEREST"
        return None

    def ask(self, slot: str, subject: SubjectState, turn: int) -> str:
        subject.pending_slot = slot
        subject.asked_slots[slot] = turn
        subject.last_question_asked = QUESTIONS[slot]
        return QUESTIONS[slot]
