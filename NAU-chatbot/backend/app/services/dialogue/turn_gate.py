from __future__ import annotations

import re
from enum import Enum

from app.core.file_config import pattern_file, security_file_config
from app.services.dialogue.normalizer import contains_phrase, fold_text


class TurnType(str, Enum):
    EMPTY = "EMPTY"
    RESET = "RESET"
    SECURITY = "SECURITY"
    INAPPROPRIATE = "INAPPROPRIATE"
    GREETING = "GREETING"
    HOW_ARE_YOU = "HOW_ARE_YOU"
    THANKS = "THANKS"
    GOODBYE = "GOODBYE"
    SMALL_TALK = "SMALL_TALK"
    ACADEMIC = "ACADEMIC"


FIXED_RESPONSES = {
    TurnType.EMPTY: "Écris-moi simplement ce que tu aimerais savoir sur les formations à l'IIT.",
    TurnType.SECURITY: "Je ne peux pas révéler des accès, endpoints, secrets ou configurations internes, ni exécuter des requêtes. Je peux toutefois t'aider sur ton orientation et les formations de l'IIT.",
    TurnType.INAPPROPRIATE: "Merci de rester respectueux. Je peux continuer à t'aider sur ton orientation et les formations si tu souhaites poursuivre.",
    TurnType.GREETING: "Salut 🙂 Qu'est-ce que tu aimerais savoir sur les formations à l'IIT ?",
    TurnType.HOW_ARE_YOU: "Salut 🙂 Ça va bien, merci. Et toi, qu'est-ce que tu aimerais explorer à l'IIT ?",
    TurnType.THANKS: "Avec plaisir 🙂 N'hésite pas si tu veux approfondir une formation.",
    TurnType.GOODBYE: "À bientôt 🙂 Bon courage pour ton orientation !",
    TurnType.SMALL_TALK: "Salut 🙂 Je suis là pour t'aider à explorer les formations et ton orientation à l'IIT.",
    TurnType.RESET: "D'accord, on repart de zéro. Qu'est-ce que tu aimerais savoir ?",
}


class TurnGate:
    def __init__(self) -> None:
        greeting = pattern_file("greetings").patterns
        self.patterns = {
            name: [re.compile(item, re.IGNORECASE) for item in values]
            for name, values in greeting.items()
        }
        self.smalltalk = [
            re.compile(item, re.IGNORECASE)
            for item in pattern_file("smalltalk").patterns.get("smalltalk", [])
        ]
        self.hints = {
            fold_text(term)
            for term in pattern_file("smalltalk").terms.get("academic_hints", [])
        }
        contextual = pattern_file("contextual_modifiers").terms
        self.contextual_terms = tuple(
            term for values in contextual.values() for term in values
        )
        self.insults = [
            re.compile(item, re.IGNORECASE)
            for item in pattern_file("insults").patterns.get("inappropriate", [])
        ]
        self.security = [
            re.compile(item, re.IGNORECASE)
            for item in pattern_file("security").patterns.get("injection", [])
        ]
        self.max_chars = security_file_config().max_message_chars

    def classify(self, message: str) -> TurnType:
        raw = (message or "").strip()
        if not raw:
            return TurnType.EMPTY
        if len(raw) > self.max_chars:
            return TurnType.SECURITY
        folded = fold_text(raw)
        if self._matches("reset", folded):
            return TurnType.RESET
        if any(pattern.search(folded) for pattern in self.security):
            return TurnType.SECURITY
        if any(pattern.search(folded) for pattern in self.insults):
            return TurnType.INAPPROPRIATE
        for name, kind in (
            ("greeting", TurnType.GREETING),
            ("how_are_you", TurnType.HOW_ARE_YOU),
            ("thanks", TurnType.THANKS),
            ("goodbye", TurnType.GOODBYE),
        ):
            if self._matches(name, folded):
                return kind
        if any(pattern.search(folded) for pattern in self.smalltalk):
            return TurnType.SMALL_TALK
        if any(contains_phrase(folded, term) for term in self.contextual_terms):
            return TurnType.ACADEMIC
        words = set(folded.split())
        if len(words) <= 2 and words and not words.intersection(self.hints):
            return TurnType.SMALL_TALK
        return TurnType.ACADEMIC

    def _matches(self, name: str, value: str) -> bool:
        return any(pattern.search(value) for pattern in self.patterns.get(name, []))

    def response(self, turn_type: TurnType, *, first_reply: bool) -> str:
        answer = FIXED_RESPONSES[turn_type]
        if not first_reply:
            answer = {
                TurnType.GREETING: "Je suis toujours là 🙂 Que veux-tu approfondir sur l'IIT ?",
                TurnType.HOW_ARE_YOU: "Ça va bien, merci 🙂 Que veux-tu approfondir sur l'IIT ?",
                TurnType.SMALL_TALK: "Je suis là pour continuer ton orientation à l'IIT.",
            }.get(turn_type, answer)
        if first_reply and not fold_text(answer).startswith("salut"):
            return f"Salut 🙂 {answer}"
        return answer
