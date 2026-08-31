from __future__ import annotations

from enum import Enum

from app.services.dialogue.contextual_modifier import ContextScope
from app.services.dialogue.negation_detector import NegationResult
from app.services.dialogue.normalizer import contains_phrase, fold_text


class DialogueAct(str, Enum):
    ASK_INFORMATION = "ASK_INFORMATION"
    ANSWER_SLOT = "ANSWER_SLOT"
    REQUEST_RECOMMENDATION = "REQUEST_RECOMMENDATION"
    REQUEST_MORE_DETAILS = "REQUEST_MORE_DETAILS"
    REQUEST_ALTERNATIVE = "REQUEST_ALTERNATIVE"
    EXPRESS_INTEREST = "EXPRESS_INTEREST"
    EXPRESS_DIFFICULTY = "EXPRESS_DIFFICULTY"
    REJECT_QUESTION = "REJECT_QUESTION"
    DISAGREE = "DISAGREE"


class DialogueActDetector:
    def detect(
        self,
        original_message: str,
        *,
        auxiliary_interpretation: str = "",
        scope: ContextScope,
        negation: NegationResult,
        pending_parsed: bool,
    ) -> DialogueAct:
        text = fold_text(original_message)
        auxiliary = fold_text(auxiliary_interpretation)
        if pending_parsed:
            return DialogueAct.ANSWER_SLOT
        if negation.request_alternative or scope is ContextScope.OTHER:
            return DialogueAct.REQUEST_ALTERNATIVE
        if scope is ContextScope.MORE:
            return DialogueAct.REQUEST_MORE_DETAILS
        if negation.rejected_offers or negation.rejected_domains:
            return DialogueAct.DISAGREE
        if any(
            contains_phrase(text, term)
            for term in (
                "recommande",
                "conseille",
                "choisir",
                "tranche",
                "je suis perdu",
                "choufli",
                "tansahni",
                "chtansahni",
                "chtnsahni",
            )
        ) or any(
            contains_phrase(auxiliary, term)
            for term in ("recommande", "choisir", "orientation")
        ):
            return DialogueAct.REQUEST_RECOMMENDATION
        if any(
            contains_phrase(text, term)
            for term in ("difficile", "peur", "math faible", "dur")
        ) or any(
            contains_phrase(auxiliary, term) for term in ("difficile", "peur")
        ):
            return DialogueAct.EXPRESS_DIFFICULTY
        if any(
            contains_phrase(text, term)
            for term in ("interesse", "intéressé", "nhebha", "ca me plait", "ça me plaît")
        ):
            return DialogueAct.EXPRESS_INTEREST
        return DialogueAct.ASK_INFORMATION
