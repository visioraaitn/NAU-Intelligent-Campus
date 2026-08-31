from __future__ import annotations

import re
import unicodedata


def fold_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    lowered = without_marks.lower().replace("’", "'")
    lowered = re.sub(r"[^a-z0-9'\s]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def token_set(value: str) -> set[str]:
    return set(fold_text(value).split())


def contains_phrase(folded_text: str, phrase: str) -> bool:
    """Match a normalized word or phrase without accidental substring hits."""

    needle = fold_text(phrase)
    return bool(needle) and f" {needle} " in f" {folded_text} "
