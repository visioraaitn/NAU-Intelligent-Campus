from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.file_config import dialogue_config, pattern_file
from app.domain.conversation.models import AcademicProfile, ConversationSubject
from app.services.dialogue.contextual_modifier import ContextScope, ContextualModifierDetector
from app.services.dialogue.negation_detector import NegationResult
from app.services.dialogue.normalizer import contains_phrase, fold_text, normalize_degree_spelling


@dataclass(frozen=True, slots=True)
class RawFacts:
    subject: ConversationSubject
    profile: AcademicProfile | None = None
    bac_specialty: str | None = None
    bac_average: float | None = None
    math_grade: float | None = None
    licence_specialty: str | None = None
    licence_year: int | None = None
    credential_answer: bool = False
    interests: tuple[str, ...] = ()
    target: str | None = None
    finishing_current_degree: bool = False
    pre_registration_completed: bool = False
    correction: bool = False
    denies_bac: bool = False
    scope: ContextScope = ContextScope.CURRENT


class RawFactExtractor:
    def __init__(self) -> None:
        config = pattern_file("profiles")
        self.patterns = {
            name: [re.compile(item, re.I) for item in values]
            for name, values in config.patterns.items()
        }
        self.terms = config.terms
        self.interest_terms = dialogue_config().interest_keywords
        self.context = ContextualModifierDetector()

    def extract(
        self,
        message: str,
        *,
        active_subject: ConversationSubject,
        negation: NegationResult,
    ) -> RawFacts:
        text = normalize_degree_spelling(message)
        subject = self._subject(text, active_subject)
        profile = self._profile(text)
        bac = self._bac(text)
        average = self._number("average", text)
        math_grade = self._number("math_grade", text)
        licence_year = self._licence_year(text)
        # Keep clause boundaries when extracting the diploma: the following
        # question is not part of its title. Full-message intent detection
        # still sees every clause.
        licence_specialty = next((value for clause in re.split(r'[,;?!\n]', message)
                                  if (value := self._capture('licence_specialty', normalize_degree_spelling(clause)))), None)
        if (
            licence_specialty
            and self._matches("licence_holder", text)
            and re.search(r"\b(?:r[eé]ussi|valid[eé]|obtenu|termin[eé]|njaht|naj7t)\w*\b", text)
            and not re.search(r"\blicence\s+en\s+", text)
        ):
            licence_specialty = None
        interests: list[str] = []
        for interest, terms in self.interest_terms.items():
            if any(contains_phrase(text, term) for term in terms):
                # A negated preference is a rejection, never a positive fact.
                if not negation.has_negation:
                    interests.append(interest)
        target = None
        goal_cues = ("nheb", "je veux", "je souhaite", "objectif", "devenir", "nkamel", "poursuivre")
        has_goal = any(contains_phrase(text, cue) for cue in goal_cues)
        if has_goal and any(
            contains_phrase(text, term)
            for term in ("ingenieur", "ingénieur", "ingenierie", "ingénierie", "cycle ingenieur")
        ):
            target = "ENGINEERING"
        elif has_goal and (contains_phrase(text, "prepa") or contains_phrase(text, "preparatoire")):
            target = "PREPA"
        elif has_goal and contains_phrase(text, "licence"):
            target = "LICENCE"
        elif (
            has_goal
            and profile is AcademicProfile.LICENCE_STUDENT
            and not any(
                contains_phrase(text, term)
                for term in ("ingenieur", "ingénieur", "ingenierie", "ingénierie", "prepa", "preparatoire")
            )
        ):
            # "I am in licence and want to continue studying here" means
            # continuation in the licence track unless engineering is explicit.
            target = "LICENCE"
        if profile is AcademicProfile.PREPA_HOLDER and has_goal:
            target = "ENGINEERING"
        return RawFacts(
            subject=subject,
            profile=profile,
            bac_specialty=bac,
            bac_average=average,
            math_grade=math_grade,
            licence_specialty=licence_specialty,
            licence_year=licence_year,
            interests=tuple(interests),
            target=target,
            finishing_current_degree=self._matches("finishing", text),
            pre_registration_completed=self._matches(
                "pre_registration_completed",
                text,
            ),
            correction=self._matches("correction", text),
            denies_bac=self._matches("bac_denial", text),
            scope=self.context.detect(text),
        )

    def _subject(self, text: str, current: ConversationSubject) -> ConversationSubject:
        if self._matches("hypothetical", text):
            return ConversationSubject.HYPOTHETICAL
        if self._matches("friend", text):
            return ConversationSubject.FRIEND
        if self._matches("family", text):
            return ConversationSubject.FAMILY
        if self._matches("self", text):
            return ConversationSubject.SELF
        return current

    def _profile(self, text: str) -> AcademicProfile | None:
        candidates: list[AcademicProfile] = []
        if self._matches("master", text) and any(
            contains_phrase(text, cue)
            for cue in ("ena", "je suis", "j'ai", "j ai", "andi", "3andi", "i have", "i am")
        ):
            candidates.append(AcademicProfile.MASTER_HOLDER)
        if self._matches("licence_holder", text):
            candidates.append(AcademicProfile.LICENCE_HOLDER)
        elif self._matches("licence_student", text):
            candidates.append(AcademicProfile.LICENCE_STUDENT)
        if self._matches("prepa_holder", text):
            candidates.append(AcademicProfile.PREPA_HOLDER)
        elif self._matches("prepa_student", text):
            candidates.append(AcademicProfile.PREPA_STUDENT)
        if self._matches("bac", text) and not self._matches("bac_denial", text):
            candidates.append(AcademicProfile.NEW_BAC)
        return max(candidates, key=lambda item: item.rank) if candidates else None

    def _bac(self, text: str) -> str | None:
        for label, key in (
            ("MATH", "bac_math"),
            ("SCIENCES", "bac_sciences"),
            ("INFORMATIQUE", "bac_info"),
            ("TECHNIQUE", "bac_technique"),
            ("ECONOMIE_GESTION", "bac_eco"),
            ("LETTERS", "bac_letters"),
            ("SPORT", "bac_sport"),
        ):
            if any(contains_phrase(text, term) for term in self.terms.get(key, [])):
                return label
        return None

    def _number(self, name: str, text: str) -> float | None:
        for pattern in self.patterns.get(name, []):
            match = pattern.search(text)
            if match:
                value = float(match.group("value").replace(",", "."))
                return value if 0 <= value <= 20 else None
        return None

    def _licence_year(self, text: str) -> int | None:
        for pattern in self.patterns.get("licence_year", []):
            match = pattern.search(text)
            if match:
                return int(match.group("value"))
        return None

    def _capture(self, name: str, text: str) -> str | None:
        for pattern in self.patterns.get(name, []):
            match = pattern.search(text)
            if match:
                value = match.group("value").strip()
                padded = f" {value} "
                stops = [
                    padded.find(f" {fold_text(term)} ")
                    for term in self.terms.get("capture_stop", [])
                    if padded.find(f" {fold_text(term)} ") >= 0
                ]
                if stops:
                    value = padded[1 : min(stops)].strip()
                value = re.sub(
                    r"^(?:[1-3](?:er|ere|ère|eme|ème|e)?|l[1-3])[_\s-]+",
                    "",
                    value,
                    flags=re.I,
                )
                value = re.sub(
                    r"[_\s-]+(?:l[1-3]|[1-3](?:er|ere|ère|eme|ème|e)?)$",
                    "",
                    value,
                    flags=re.I,
                )
                if fold_text(value) in {"w", "wa", "fi", "fel", "en"}:
                    return None
                return value[:80].upper().replace(" ", "_") or None
        return None

    def _matches(self, name: str, text: str) -> bool:
        return any(pattern.search(text) for pattern in self.patterns.get(name, []))
