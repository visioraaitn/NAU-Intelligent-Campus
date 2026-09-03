from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.conversation.models import AcademicProfile, SubjectState
from app.core.file_config import pattern_file
from app.services.dialogue.normalizer import contains_phrase, fold_text


@dataclass(frozen=True, slots=True)
class PendingSlotResult:
    parsed: bool = False
    previous_intents: tuple[str, ...] = ()
    forced_intents: tuple[str, ...] = ()


class PendingSlotResolver:
    AFFIRMATIVE_PATTERN = re.compile(r"^(?:oui+|yes|ey+|eey+|behi|d'accord|ok+)$", re.I)

    def __init__(self) -> None:
        self.pair_patterns = [
            re.compile(value, re.I)
            for value in pattern_file("profiles").patterns["pending_bac_level"]
        ]

    def resolve(self, message: str, state: SubjectState) -> PendingSlotResult:
        folded = fold_text(message).strip()
        if state.pending_action:
            action = state.pending_action
            state.pending_action = None
            if self.is_affirmative(folded):
                return PendingSlotResult(
                    parsed=True,
                    previous_intents=tuple(state.last_intents),
                    forced_intents=(action,),
                )
        slot = state.pending_slot
        if not slot:
            return PendingSlotResult()
        previous = tuple(state.last_intents)
        parsed_slots = {
            "PROFILE": state.profile is not AcademicProfile.UNKNOWN,
            "BAC_SPECIALTY": bool(state.bac_specialty),
            "LICENCE_SPECIALTY": bool(state.licence_specialty),
            "INTEREST": bool(state.interests),
        }
        if parsed_slots.get(slot, False):
            state.pending_slot = None
            return PendingSlotResult(True, previous)
        if slot == "BAC_SPECIALTY":
            aliases = (
                ("MATH", ("math", "maths", "mathematiques", "رياضيات")),
                ("SCIENCES", ("science", "sciences", "sciences experimentales", "علوم")),
                ("INFORMATIQUE", ("info", "informatique", "اعلامية", "إعلامية")),
                ("TECHNIQUE", ("technique", "sciences techniques", "تقنية")),
                ("ECONOMIE_GESTION", ("eco", "economie", "gestion", "اقتصاد", "تصرف")),
                ("LETTERS", ("lettre", "lettres", "litteraire", "آداب")),
                ("SPORT", ("sport", "رياضة")),
            )
            specialty = next(
                (
                    code
                    for code, terms in aliases
                    if any(contains_phrase(folded, term) for term in terms)
                ),
                None,
            )
            if specialty:
                state.bac_specialty = specialty
                state.pending_slot = None
                return PendingSlotResult(True, previous)
        if slot == "BAC_LEVEL":
            match = next((pattern.match(folded) for pattern in self.pair_patterns if pattern.match(folded)), None)
            if match:
                average = float(match.group("average").replace(",", "."))
                math = float(match.group("math").replace(",", "."))
                if 0 <= average <= 20 and 0 <= math <= 20:
                    state.bac_average = average
                    state.math_grade = math
                    state.math_comfort = "HIGH" if math >= 14 else "MEDIUM" if math >= 10 else "LOW"
                    state.pending_slot = None
                    return PendingSlotResult(True, previous)
        return PendingSlotResult(False, previous)

    @classmethod
    def is_affirmative(cls, message: str) -> bool:
        return bool(cls.AFFIRMATIVE_PATTERN.fullmatch(fold_text(message).strip()))
