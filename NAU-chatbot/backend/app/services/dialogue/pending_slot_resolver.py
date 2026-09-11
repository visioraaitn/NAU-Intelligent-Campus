from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.domain.conversation.models import AcademicProfile, SubjectState
from app.core.file_config import pattern_file
from app.services.dialogue.normalizer import contains_phrase, fold_text


@dataclass(frozen=True, slots=True)
class PendingSlotResult:
    parsed: bool = False
    previous_intents: tuple[str, ...] = ()
    forced_intents: tuple[str, ...] = ()


class PendingSlotResolver:
    AFFIRMATIVE_PATTERN = re.compile(r"^(?:(?:bh|beh|behi)\s+)?(?:oui+|yes|ey+|eey+|ay+h?|eyh|be+hi|d'accord|ok+)$", re.I)

    def __init__(self) -> None:
        self.pair_patterns = [
            re.compile(value, re.I)
            for value in pattern_file("profiles").patterns["pending_bac_level"]
        ]

    def resolve(self, message: str, state: SubjectState, *, provided_fields: set[str] | None = None) -> PendingSlotResult:
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
        # These qualification slots belong to orientation, even if a factual
        # question or registration request intervened before the answer.
        previous = ("ORIENTATION",) if slot in {"PROFILE", "BAC_SPECIALTY", "LICENCE_SPECIALTY", "INTEREST"} else tuple(state.last_intents)
        parsed_slots = {
            "PROFILE": state.profile is not AcademicProfile.UNKNOWN,
            "BAC_SPECIALTY": bool(state.bac_specialty),
            "LICENCE_SPECIALTY": bool(state.licence_specialty) and (provided_fields is None or 'licence_specialty' in provided_fields),
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
        if slot == "LICENCE_SPECIALTY":
            value = re.sub(r"\s+", " ", folded).strip()
            blocked = {
                "w", "wa", "et", "nheb", "na9ra", "nkamel", "je veux",
                "je souhaite", "ingenieur", "ingénieur", "cycle ingenieur",
                "prepa", "preparatoire", "njaht", "naj7t", "valide", "validé",
                "licence",
            }
            if (
                value
                and value not in blocked
                and not any(
                    token in value.split()
                    for token in {
                        "licence", "nheb", "na9ra", "nkamel", "ingenieur", "prepa",
                        "njaht", "naj7t", "valide", "validé",
                    }
                )
            ):
                aliases = {
                    "INFO": ("info", "informatique", "informatique de gestion"),
                    "INDUSTRIELLE": ("indus", "industrielle", "industriel"),
                    "MAINTENANCE_INDUSTRIELLE": ("maintenance industrielle",),
                    "MECANIQUE": ("mecanique", "mécanique"),
                    "ELECTRIQUE": ("electrique", "électrique"),
                    "GESTION": ("gestion",),
                }
                normalized = re.sub(r"(.)\1+", r"\1", value)
                best_code, best_score = None, 0.0
                for code, candidates in aliases.items():
                    for candidate in candidates:
                        score = SequenceMatcher(None, normalized, fold_text(candidate)).ratio()
                        if score > best_score:
                            best_code, best_score = code, score
                if best_code and best_score >= 0.72:
                    state.licence_specialty = best_code
                else:
                    state.licence_specialty = value.upper().replace(" ", "_")
                state.pending_slot = None
                return PendingSlotResult(True, previous)
        return PendingSlotResult(False, previous)

    @classmethod
    def is_affirmative(cls, message: str) -> bool:
        return bool(cls.AFFIRMATIVE_PATTERN.fullmatch(fold_text(message).strip()))
