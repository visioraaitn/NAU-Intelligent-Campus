from __future__ import annotations

from collections.abc import Sequence

from app.core.file_config import dialogue_config
from app.domain.conversation.models import ConversationState, ConversationSubject, ConversionStage, SubjectState
from app.domain.recommendation.schemas import EligibilityStatus, RecommendationDecision
from app.services.dialogue.dialogue_act_detector import DialogueAct


FACTUAL_ONLY = {"FEES", "DURATION", "PROGRAMME", "CAREERS", "CERTIFICATIONS", "ACCREDITATION", "CONTACT"}


class ConversionCTA:
    def should_add(
        self,
        conversation: ConversationState,
        subject: SubjectState,
        intents: Sequence[str],
        act: DialogueAct,
        recommendation: RecommendationDecision | None,
    ) -> bool:
        config = dialogue_config()
        if conversation.active_subject is ConversationSubject.HYPOTHETICAL:
            return False
        if not recommendation or not recommendation.primary:
            return False
        if recommendation.primary.eligibility.status is not EligibilityStatus.ELIGIBLE:
            return False
        if subject.cta_count >= config.cta_max_count or conversation.turn_count - subject.last_cta_turn < config.cta_cooldown_turns:
            return False
        if set(intents).issubset(FACTUAL_ONLY):
            return False
        return (
            "PREINSCRIPTION" in intents
            or act is DialogueAct.EXPRESS_INTEREST
            or not subject.offer_intro_done
            or subject.conversion_stage in {ConversionStage.INTEREST, ConversionStage.PRE_REGISTRATION}
        )

    def add(self, answer: str, subject: SubjectState, turn: int) -> str:
        subject.cta_count += 1
        subject.last_cta_turn = turn
        subject.conversion_stage = ConversionStage.INTEREST
        return answer.rstrip() + "\nSi cette piste t'intéresse, je peux ensuite t'expliquer les étapes de pré-inscription, sans te promettre l'admission."

