from __future__ import annotations

import re
from collections.abc import Sequence

from app.core.file_config import pattern_file
from app.services.dialogue.contextual_modifier import ContextScope, ContextualModifierDetector
from app.services.dialogue.dialogue_act_detector import DialogueAct
from app.services.dialogue.normalizer import fold_text


ALLOWED_INTENTS = frozenset(
    {
        "CATALOG", "FEES", "DURATION", "PROGRAMME", "CAREERS", "MARKET",
        "CERTIFICATIONS", "INTERNATIONAL", "ACCREDITATION", "ADMISSION",
        "PAYMENT", "PREINSCRIPTION", "CONTACT", "ORIENTATION", "DETAILS",
        "DIFFICULTY", "PERSUASION", "PROFILE_RECALL",
        "PRACTICE", "PROJECTS", "INTERNSHIPS", "ALTERNANCE",
        "REGISTRATION_DOCUMENTS", "LOCATION", "SCHEDULE", "OUT_OF_SCOPE", "GENERAL",
    }
)


class IntentDetector:
    def __init__(self) -> None:
        self.context = ContextualModifierDetector()
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
        if scope is ContextScope.ALL and not direct and self.context.is_elliptical_expansion(original_message):
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
        if "REGISTRATION_DOCUMENTS" in direct and (
            re.search(r"\b(?:3amlt|amalt|deja|fait|effectue|termine)\b", text)
            or not re.search(r"\b(?:formulaire|preinscrit\w*|preiscrit\w*)\b", text)
        ):
            direct = [intent for intent in direct if intent != "PREINSCRIPTION"]
        if "SCHEDULE" in direct and "PROGRAMME" in direct:
            programme_terms = ("module", "matiere", "mawad", "programme", "contenu")
            if not any(term in text for term in programme_terms):
                direct = [intent for intent in direct if intent != "PROGRAMME"]
        if "PROGRAMME" in direct and "DETAILS" in direct:
            direct = [intent for intent in direct if intent != "DETAILS"]
        if "CATALOG" in direct and re.search(r"\b(?:lprogramme|programme)\s+(?:mte3|mtaa|de)\s+(?:l\s+)?iit\b", text):
            direct = [intent for intent in direct if intent != "PROGRAMME"]
        if "PERSUASION" in direct:
            direct = [intent for intent in direct if intent != "ORIENTATION"]
        return [intent for intent in dict.fromkeys(direct or ["GENERAL"]) if intent in ALLOWED_INTENTS]
