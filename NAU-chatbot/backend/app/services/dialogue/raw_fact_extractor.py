from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.file_config import dialogue_config, pattern_file
from app.domain.conversation.models import AcademicProfile, ConversationSubject
from app.services.dialogue.contextual_modifier import ContextScope, ContextualModifierDetector
from app.services.dialogue.negation_detector import NegationResult
from app.services.dialogue.normalizer import contains_phrase, fold_text


@dataclass(frozen=True, slots=True)
class RawFacts:
    subject: ConversationSubject
    profile: AcademicProfile | None = None
    bac_specialty: str | None = None
    bac_average: float | None = None
    math_grade: float | None = None
    licence_specialty: str | None = None
    interests: tuple[str, ...] = ()
    target: str | None = None
    finishing_current_degree: bool = False
    correction: bool = False
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
        text = fold_text(message)
        subject = self._subject(text, active_subject)
        profile = self._profile(text, negation.has_negation)
        bac = self._bac(text)
        average = self._number("average", text)
        math_grade = self._number("math_grade", text)
        licence_specialty = self._capture("licence_specialty", text)
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
        return RawFacts(
            subject=subject,
            profile=profile,
            bac_specialty=bac,
            bac_average=average,
            math_grade=math_grade,
            licence_specialty=licence_specialty,
            interests=tuple(interests),
            target=target,
            finishing_current_degree=self._matches("finishing", text),
            correction=self._matches("correction", text),
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

    def _profile(self, text: str, negated: bool) -> AcademicProfile | None:
        candidates: list[AcademicProfile] = []
        if self._matches("master", text) and any(
            contains_phrase(text, cue)
            for cue in ("ena", "je suis", "j'ai", "j ai", "andi", "3andi", "i have", "i am")
        ):
            candidates.append(AcademicProfile.MASTER_HOLDER)
        if self._matches("licence_holder", text):
            candidates.append(AcademicProfile.LICENCE_HOLDER)
        elif self._matches("licence_student", text) or (
            self._matches("licence", text)
            and any(
                contains_phrase(text, cue)
                for cue in ("ena", "je suis", "andi", "3andi", "na9ra")
            )
        ):
            candidates.append(AcademicProfile.LICENCE_STUDENT)
        if self._matches("prepa_holder", text):
            candidates.append(AcademicProfile.PREPA_HOLDER)
        elif self._matches("prepa_student", text):
            candidates.append(AcademicProfile.PREPA_STUDENT)
        if self._matches("bac", text) and not (
            negated and contains_phrase(text, "manich bac")
        ):
            candidates.append(AcademicProfile.NEW_BAC)
        return max(candidates, key=lambda item: item.rank) if candidates else None

    def _bac(self, text: str) -> str | None:
        for label, key in (
            ("MATH", "bac_math"),
            ("SCIENCES", "bac_sciences"),
            ("INFORMATIQUE", "bac_info"),
            ("TECHNIQUE", "bac_technique"),
            ("ECONOMIE_GESTION", "bac_eco"),
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
                return value[:80].upper().replace(" ", "_") or None
        return None

    def _matches(self, name: str, text: str) -> bool:
        return any(pattern.search(text) for pattern in self.patterns.get(name, []))
