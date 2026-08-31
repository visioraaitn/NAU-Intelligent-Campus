from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.file_config import pattern_file
from app.services.dialogue.normalizer import contains_phrase, fold_text


@dataclass(frozen=True, slots=True)
class NegationResult:
    has_negation: bool
    rejected_offers: tuple[str, ...]
    rejected_domains: tuple[str, ...]
    request_alternative: bool


class NegationDetector:
    def __init__(self) -> None:
        config = pattern_file("negations")
        self.negations = [re.compile(item, re.I) for item in config.patterns["negation"]]
        self.info = [re.compile(item, re.I) for item in config.patterns["reject_info"]]
        self.offer = [re.compile(item, re.I) for item in config.patterns["reject_offer"]]
        self.offers = tuple(config.terms["offers"])
        self.alternative_terms = pattern_file("contextual_modifiers").terms["other"]

    def detect(self, message: str) -> NegationResult:
        text = fold_text(message)
        has_negation = any(pattern.search(text) for pattern in self.negations)
        rejected_domains = ("INFORMATIQUE",) if any(p.search(text) for p in self.info) else ()
        rejected_offers: list[str] = []
        if any(pattern.search(text) for pattern in self.offer):
            rejected_offers = [
                offer for offer in self.offers if contains_phrase(text, offer)
            ]
        return NegationResult(
            has_negation=has_negation,
            rejected_offers=tuple(rejected_offers),
            rejected_domains=rejected_domains,
            request_alternative=any(
                contains_phrase(text, term) for term in self.alternative_terms
            ),
        )
