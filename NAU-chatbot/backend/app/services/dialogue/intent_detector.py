from __future__ import annotations

import re
from collections.abc import Sequence

from app.core.file_config import pattern_file
from app.services.dialogue.contextual_modifier import ContextScope
from app.services.dialogue.dialogue_act_detector import DialogueAct
from app.services.dialogue.normalizer import fold_text


ALLOWED_INTENTS = frozenset(
    {
        "CATALOG", "FEES", "DURATION", "PROGRAMME", "CAREERS", "MARKET",
        "CERTIFICATIONS", "INTERNATIONAL", "ACCREDITATION", "ADMISSION",
        "PAYMENT", "PREINSCRIPTION", "CONTACT", "ORIENTATION", "DETAILS",
        "DIFFICULTY", "PERSUASION", "PROFILE_RECALL",
        "REGISTRATION_DOCUMENTS", "GENERAL",
    }
)


class IntentDetector:
    def __init__(self) -> None:
        self.patterns = {
            intent: [re.compile(value, re.I) for value in values]
            for intent, values in pattern_file("intents").patterns.items()
        }

    def detect(
        self,
        original_message: str,
        *,
        auxiliary_interpretation: str = "",
        previous: Sequence[str],
        scope: ContextScope,
        dialogue_act: DialogueAct,
        slot_parsed: bool,
    ) -> list[str]:
        text = fold_text(original_message)
        direct = [
            intent
            for intent, patterns in self.patterns.items()
            if any(pattern.search(text) for pattern in patterns)
        ]
        if slot_parsed and not direct:
            direct = list(previous or ("ORIENTATION",))
        elif not direct and auxiliary_interpretation:
            auxiliary = fold_text(auxiliary_interpretation)
            direct = [
                intent
                for intent, patterns in self.patterns.items()
                if any(pattern.search(auxiliary) for pattern in patterns)
            ]
        if scope is ContextScope.ALL and not direct:
            direct = list(previous or ("GENERAL",))
        elif scope is ContextScope.MORE:
            direct = list(dict.fromkeys(("DETAILS", *(direct or previous or ("GENERAL",)))))
        if dialogue_act in {
            DialogueAct.REQUEST_RECOMMENDATION,
            DialogueAct.REQUEST_ALTERNATIVE,
        } and "ORIENTATION" not in direct:
            direct.insert(0, "ORIENTATION")
        if dialogue_act is DialogueAct.EXPRESS_DIFFICULTY and "DIFFICULTY" not in direct:
            direct.append("DIFFICULTY")
        if "REGISTRATION_DOCUMENTS" in direct:
            direct = [intent for intent in direct if intent != "PREINSCRIPTION"]
        return [intent for intent in dict.fromkeys(direct or ["GENERAL"]) if intent in ALLOWED_INTENTS]
