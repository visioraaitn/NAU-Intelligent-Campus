from __future__ import annotations

from enum import Enum

from app.core.file_config import pattern_file
from app.services.dialogue.normalizer import contains_phrase, fold_text


class ContextScope(str, Enum):
    CURRENT = "CURRENT"
    ALL = "ALL"
    OTHER = "OTHER"
    MORE = "MORE"


class ContextualModifierDetector:
    def __init__(self) -> None:
        self.terms = pattern_file("contextual_modifiers").terms

    def detect(self, message: str) -> ContextScope:
        folded = fold_text(message)
        for scope in (ContextScope.ALL, ContextScope.OTHER, ContextScope.MORE):
            if any(
                contains_phrase(folded, term)
                for term in self.terms.get(scope.value.lower(), [])
            ):
                return scope
        return ContextScope.CURRENT

    def is_elliptical_expansion(self, message: str) -> bool:
        """Only a standalone scope expression may inherit the previous topic."""
        text = fold_text(message).strip(" .!?،؟")
        return any(text == fold_text(term) for term in self.terms.get("all", []))
