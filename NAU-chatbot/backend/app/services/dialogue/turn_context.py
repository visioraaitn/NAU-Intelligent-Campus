from __future__ import annotations

import re

from app.services.dialogue.normalizer import fold_text


class TurnContextPolicy:
    """Linguistic permission to read topic memory, never evidence of a domain.

    A short message is not sufficient: after removing recognized intent spans,
    only grammatical glue may remain. Unknown content needs semantic routing.
    """

    GLUE = frozenset("et w wa wel el les le la l des de du d en pour un une quels quelles quel quelle sont est c ce ca a au aux il y t on me moi tu vous je peux peut donne donner dis dire stp svp aussi alors the and what about les tous toutes tout plus davantage encore fiha biha hedhi hedha mte3 mtaa walla wella ou".split())
    GLUE |= frozenset("atini aatini kifeh naml nice beeh beh bh nhebek elli kol chnouma chnoua fi hal 3amlt source sources lien site page officiel officielle".split())
    REFERENCE = re.compile(
        r"\b(?:cette formation|cette licence|ce parcours|cette specialite|celle ci|"
        r"celui ci|elle|fiha|biha|hedhi|hedha|hal option|sa duree|son programme|ses frais)\b"
        r"|\b(?:les? matieres?|mawad|competences?|certifications?|debouches?|"
        r"frais|tarif|admission|inscription|preinscription|"
        r"mo3taraf|mo3taref|ma3tref|ma3rouf|reconnu\w*|accredit\w*)\b"
    )

    @classmethod
    def intent_only(cls, message: str, patterns: dict) -> bool:
        remainder = fold_text(message)
        matched = False
        for intent, expressions in patterns.items():
            if intent in {"GENERAL", "OUT_OF_SCOPE"}:
                continue
            for expression in expressions:
                remainder, count = expression.subn(" ", remainder)
                matched |= count > 0
        return matched and set(remainder.split()) <= cls.GLUE

    @classmethod
    def allows_topic(cls, message: str, patterns: dict, *, expansion: bool = False,
                     pending_answer: bool = False) -> bool:
        text = fold_text(message)
        if pending_answer or expansion or cls.REFERENCE.search(text):
            return True
        # Complete questions without a referent must ask for their own scope.
        return len(text.split()) <= 12 and cls.intent_only(message, patterns)
