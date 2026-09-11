from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher


def fold_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    lowered = without_marks.lower().replace("’", "'")
    lowered = re.sub(r"[^a-z0-9\u0600-\u06ff'\s]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def token_set(value: str) -> set[str]:
    return set(fold_text(value).split())


def normalize_degree_spelling(value: str) -> str:
    """Normalize close degree-name typos, without inferring a completed degree."""
    words = fold_text(value).split()
    words = ["licence" if word in {"license", "licenses"} else word for word in words]
    for index, word in enumerate(words):
        if 6 <= len(word) <= 10:
            scores = sorted((SequenceMatcher(None, word, name).ratio(), name)
                            for name in ('licence', 'mastere', 'ingenieur'))
            if word[:3] == scores[-1][1][:3] and scores[-1][0] >= .85 and scores[-1][0] - scores[-2][0] >= .1:
                words[index] = scores[-1][1]
    return ' '.join(words)


def contains_phrase(folded_text: str, phrase: str) -> bool:
    """Match a normalized word or phrase without accidental substring hits."""

    needle = fold_text(phrase)
    return bool(needle) and f" {needle} " in f" {folded_text} "
