from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from enum import Enum
from itertools import groupby

from app.core.file_config import pattern_file, security_file_config
from app.services.dialogue.normalizer import contains_phrase, fold_text, normalize_degree_spelling


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
    ACKNOWLEDGEMENT = "ACKNOWLEDGEMENT"
    CLARIFICATION = "CLARIFICATION"
    IDENTITY = "IDENTITY"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
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
    TurnType.ACKNOWLEDGEMENT: "D'accord 🙂 On peut continuer quand tu veux : quelle information souhaites-tu approfondir ?",
    TurnType.CLARIFICATION: "Tu veux que je précise ou reformule un point ? Dis-moi lequel et je reprends l'explication.",
    TurnType.IDENTITY: "Je suis l'assistant virtuel de l'IIT. Je peux t'aider à comparer les formations, comprendre leurs programmes et préparer ton orientation ou ton admission.",
    TurnType.OUT_OF_SCOPE: "Je peux aider uniquement pour les formations, l'orientation, l'admission, les modules, les frais et les informations officielles de l'IIT.",
    TurnType.RESET: "D'accord, on repart de zéro. Qu'est-ce que tu aimerais savoir ?",
}


class TurnGate:
    # These cues are deliberately narrower than intent detection.  They are used
    # to override a fallible model domain decision, so generic words such as
    # "programme", "travail", "avenir" or "combien" must not be included.
    STRONG_ACADEMIC_SIGNAL = re.compile(
        r"\b(?:iit|bac(?:calaureat)?|licen[cs]e|mastere?|prepa|preparatoire|"
        r"formations?|specialites?|filieres?|parcours|genie|ingenieur|architecture|"
        r"matieres?|modules?|diplome|admission|admissible|pre[ -]?inscri\w*|"
        r"mensualites?|tarifs?|b?9add?e(?:h|ch)|accredit\w*|certifications?|certifs?|campus|"
        r"mo3taraf|mo3taref|ma3tref|ma3rouf|معترف|"
        r"cours?\s+(?:du|de)?\s*soir[e]?|"
        r"(?:na9ra|n9ra|nakra|nkra)\s+(?:b|bel|fi|fel)\s*(?:el\s*)?lil|"
        r"nej+em\s+na9ra|nej+em\s+n9ra|nheb\s+na9ra|nheb\s+n9ra|nheb\s+nkra|"
        r"informatique|cyber(?:securite)?|mecatronique|electrique|industriel|"
        r"science\s+des\s+donnees|intelligence\s+artificielle)\b",
        re.I,
    )

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
        self.insult_vocabulary = tuple(pattern_file("insults").terms.get("vocabulary", []))
        self.insult_phonetics = {
            self._consonants(self._compact_lexeme(word))
            for word in pattern_file("insults").terms.get("phonetic_vocabulary", [])
            if len(self._consonants(self._compact_lexeme(word))) >= 3
        }
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
        if any(pattern.search(folded) for pattern in self.insults) or self._similar_insult(folded) or self._similar_insult(self._unmask_insults(raw)):
            return TurnType.INAPPROPRIATE
        if self._has_intent("OUT_OF_SCOPE", folded):
            return TurnType.OUT_OF_SCOPE
        if len(folded) >= 3 and len(set(folded)) == 1:
            return TurnType.CLARIFICATION
        if normalize_degree_spelling(raw) != folded:
            return TurnType.ACADEMIC
        if self.has_strong_academic_signal(raw):
            return TurnType.ACADEMIC
        if re.fullmatch(r"w(?:i|e)n(?:e?k|ik)?\s+cv", folded):
            return TurnType.HOW_ARE_YOU
        # A short academic word (e.g. "tarifs") must not fuzzy-match "salut".
        if self._has_academic_intent(folded):
            return TurnType.ACADEMIC
        fuzzy_social = self._fuzzy_social_type(folded)
        if fuzzy_social is not None:
            return fuzzy_social
        for name, kind in (
            ("greeting", TurnType.GREETING),
            ("how_are_you", TurnType.HOW_ARE_YOU),
            ("thanks", TurnType.THANKS),
            ("goodbye", TurnType.GOODBYE),
        ):
            if self._matches(name, folded):
                return kind
        if self._has_academic_intent(folded):
            return TurnType.ACADEMIC
        if any(pattern.search(folded) for pattern in self.smalltalk):
            return TurnType.SMALL_TALK
        if any(contains_phrase(folded, term) for term in self.contextual_terms):
            return TurnType.ACADEMIC
        words = set(folded.split())
        if len(words) <= 2 and words and not words.intersection(self.hints):
            return TurnType.SMALL_TALK
        return TurnType.ACADEMIC

    @staticmethod
    def _compact_lexeme(word: str) -> str:
        return "".join(char for char, _ in groupby(word.translate(str.maketrans({'3': 'a', '7': 'h', '9': 'q'}))))

    @staticmethod
    def _consonants(word: str) -> str:
        return word.translate(str.maketrans('', '', 'aeiou'))

    @staticmethod
    def _unmask_insults(message: str) -> str:
        # This view is used only for moderation; preserve the original message
        # for academic interpretation and profile extraction.
        visible = ''.join(char for char in unicodedata.normalize('NFKC', message)
                          if unicodedata.category(char) != 'Cf')
        visible = re.sub(r'(?<=\w)[^\w\s]+(?=\w)', '', visible)
        return fold_text(visible)

    def _similar_insult(self, value: str) -> bool:
        """Catch repetition, masking and reviewed phonetic spelling variants."""
        candidates = tuple(self._compact_lexeme(word) for word in self.insult_vocabulary)
        words = value.split()
        # Letter-by-letter spelling must not evade the same lexeme check.
        # Never concatenate ordinary words or an entire sentence.
        spelled_words = []
        for single_letters, run in groupby(words, key=lambda word: len(word) == 1 and word.isalpha()):
            letters = list(run)
            if single_letters and 3 <= len(letters) <= 16:
                spelled_words.append(''.join(letters))
        for word in words + spelled_words:
            token = self._compact_lexeme(word)
            if 3 <= len(token) <= 8 and self._consonants(token) in self.insult_phonetics:
                return True
            for candidate in candidates:
                if token == candidate:
                    return True
                if token.endswith(candidate) and token[:-len(candidate)] in {"a", "ae", "al", "ال"}:
                    return True
                forms = [token]
                if token.startswith("el"):
                    forms.append(token[2:])
                elif token.startswith("e"):
                    forms.append(token[1:])
                if candidate in forms:
                    return True
                if len(candidate) >= 5 and abs(len(token) - len(candidate)) <= 2 and SequenceMatcher(None, token, candidate).ratio() >= .86:
                    return True
        return False

    def _has_academic_intent(self, value: str) -> bool:
        patterns = pattern_file("intents").patterns
        academic_intents = {
            name for name in patterns
            if name not in {"GENERAL", "OUT_OF_SCOPE"}
        }
        return any(
            re.search(pattern, value, re.IGNORECASE)
            for name in academic_intents
            for pattern in patterns[name]
        )

    @staticmethod
    def _has_intent(name: str, value: str) -> bool:
        return any(
            re.search(pattern, value, re.IGNORECASE)
            for pattern in pattern_file("intents").patterns.get(name, [])
        )

    def has_strong_academic_signal(self, value: str) -> bool:
        """Return whether the message itself clearly concerns IIT/academics.

        This is intentionally independent from conversation memory: a previous
        academic profile must never turn a new weather, sport or political
        question into an academic request.
        """

        folded = fold_text(value)
        if self.STRONG_ACADEMIC_SIGNAL.search(folded):
            return True
        academic_words = (
            "genie", "ingenieur", "informatique", "industriel", "licence",
            "specialite",
        )
        return any(
            len(token) >= 4
            and max(SequenceMatcher(None, token, word).ratio() for word in academic_words) >= .78
            for token in folded.split()
        )

    def _fuzzy_social_type(self, value: str) -> TurnType | None:
        if len(value) > 32 or not value.isascii():
            return None
        candidates = {
            TurnType.HOW_ARE_YOU: ("cv", "ca va", "labes", "chhalek"),
            TurnType.GREETING: ("salam", "salut", "ahla", "bonjour"),
        }
        if re.fullmatch(r"w(?:i|e)n(?:e?k|ik)?\s+cv", value):
            return TurnType.HOW_ARE_YOU
        # Repeated keystrokes carry little information in short social text.
        # Compare normalized spellings dynamically instead of listing variants.
        compact = "".join(character for character, _ in groupby(value))
        for kind, words in candidates.items():
            if any(
                max(SequenceMatcher(None, value, word).ratio(),
                    SequenceMatcher(None, compact, "".join(c for c, _ in groupby(word))).ratio()) >= 0.8
                for word in words
            ):
                return kind
        return None

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
        return answer
