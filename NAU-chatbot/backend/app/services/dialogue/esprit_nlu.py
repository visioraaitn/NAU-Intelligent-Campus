from __future__ import annotations

import json
import re
from dataclasses import dataclass
from collections import OrderedDict
from time import monotonic
from hashlib import sha256

from app.core.file_config import prompt_text
from app.services.llm.providers import LLMMessage, LLMProvider


@dataclass(frozen=True, slots=True)
class DomainClassification:
    label: str
    confidence: float
    iit_signal: bool = False


@dataclass(frozen=True, slots=True)
class SemanticUnderstanding:
    domain: DomainClassification
    normalized: str
    intents: tuple[str, ...] = ()
    social: str = ""


# Bounded, short-lived cache contains linguistic interpretations, never answers
# or catalogue facts. Context is part of the key to avoid crossing subjects.
_semantic_cache: OrderedDict[str, tuple[float, SemanticUnderstanding]] = OrderedDict()


class EspritNluService:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def understand_credential(self, message: str) -> str | None:
        raw = await self.provider.generate('esprit', (
            LLMMessage('system', prompt_text('credential_understanding')),
            LLMMessage('user', message),
        ), max_new_tokens=65)
        payload = json.loads(raw)
        specialty = payload.get('specialty', '')
        confidence = float(payload.get('confidence', 0))
        if not isinstance(specialty, str) or len(specialty) > 80 or not 0 <= confidence <= 1:
            raise ValueError('invalid credential interpretation')
        if confidence < .8 or not specialty.strip():
            return None
        from difflib import SequenceMatcher
        from app.services.dialogue.normalizer import fold_text
        source_words = fold_text(message).split()
        # The local model can expand "industrielle" into "maintenance
        # industrielle" despite instructions. Keep only grounded title words;
        # an unsupported addition must never establish admission eligibility.
        grounded = [word for word in fold_text(specialty).split() if any(
            word == original or (len(word) >= 5 and len(original) >= 5
                and word[:3] == original[:3] and SequenceMatcher(None, word, original).ratio() >= .85)
            for original in source_words
        )]
        return '_'.join(grounded).upper() or None

    async def understand_social(self, message: str) -> SemanticUnderstanding | None:
        key = "social:" + sha256(message.encode()).hexdigest()
        cached = _semantic_cache.get(key)
        if cached and monotonic() - cached[0] < 600:
            _semantic_cache.move_to_end(key)
            return cached[1]
        raw = await self.provider.generate("esprit", (
            LLMMessage("system", prompt_text("social_understanding")),
            LLMMessage("user", message),
        ), max_new_tokens=45)
        payload = json.loads(raw)
        kind = payload.get("kind")
        confidence = float(payload.get("confidence", 0))
        if kind not in {"GREETING", "HOW_ARE_YOU", "THANKS", "GOODBYE", "ACKNOWLEDGEMENT", "CLARIFICATION", "IDENTITY", "INAPPROPRIATE", "UNKNOWN"} or not 0 <= confidence <= 1:
            raise ValueError("invalid social classification")
        if kind == "UNKNOWN" or confidence < .8:
            return None
        result = SemanticUnderstanding(
            DomainClassification("INAPPROPRIATE" if kind == "INAPPROPRIATE" else "SOCIAL", confidence),
            "", (), "" if kind == "INAPPROPRIATE" else kind,
        )
        _semantic_cache[key] = (monotonic(), result)
        while len(_semantic_cache) > 128:
            _semantic_cache.popitem(last=False)
        return result

    async def understand(self, message: str, context: str = "") -> SemanticUnderstanding:
        from app.services.dialogue.intent_detector import ALLOWED_INTENTS
        context = context[-600:]
        key = sha256(json.dumps([message, context], ensure_ascii=False).encode()).hexdigest()
        cached = _semantic_cache.get(key)
        if cached and monotonic() - cached[0] < 600:
            _semantic_cache.move_to_end(key)
            return cached[1]
        raw = await self.provider.generate(
            "esprit",
            (LLMMessage("system", prompt_text("semantic_understanding")),
             LLMMessage("user", json.dumps({"message": message, "context": context}, ensure_ascii=False))),
            max_new_tokens=180,
        )
        payload = json.loads(raw)
        label = payload.get("label")
        confidence = float(payload.get("confidence", 0))
        if label not in {"IN_SCOPE", "OUT_OF_SCOPE", "UNCLEAR", "SOCIAL", "INAPPROPRIATE"} or not 0 <= confidence <= 1:
            raise ValueError("invalid semantic classification")
        normalized = payload.get("normalized", "")
        intents = payload.get("intents", [])
        social = payload.get("social", "")
        if not isinstance(normalized, str) or len(normalized) > 2000 or not isinstance(intents, list):
            raise ValueError("invalid semantic interpretation")
        if any(not isinstance(intent, str) or intent not in ALLOWED_INTENTS for intent in intents):
            raise ValueError("unknown semantic intent")
        if social not in {"", "GREETING", "HOW_ARE_YOU", "THANKS", "GOODBYE", "SMALL_TALK", "ACKNOWLEDGEMENT", "CLARIFICATION", "IDENTITY"}:
            raise ValueError("unknown social act")
        result = SemanticUnderstanding(
            DomainClassification(label, confidence, payload.get("iit_signal") is True),
            normalized, tuple(dict.fromkeys(intents)), social,
        )
        if confidence >= .8:
            _semantic_cache[key] = (monotonic(), result)
            while len(_semantic_cache) > 128:
                _semantic_cache.popitem(last=False)
        return result

    async def interpret(self, original_message: str) -> str:
        return await self.provider.generate(
            "esprit",
            (
                LLMMessage("system", prompt_text("esprit_nlu")),
                LLMMessage("user", original_message),
            ),
            max_new_tokens=110,
        )

    async def classify_domain(self, original_message: str) -> DomainClassification:
        raw = await self.provider.generate(
            "esprit",
            (
                LLMMessage("system", prompt_text("domain_gate")),
                LLMMessage("user", original_message),
            ),
            max_new_tokens=60,
        )
        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            match = re.search(r"\b(IN_SCOPE|OUT_OF_SCOPE|UNCLEAR)\b", raw.upper())
            if not match:
                raise ValueError("domain classifier returned no valid label")
            return DomainClassification(match.group(1), 0.5, False)
        label = str(payload.get("label", "UNCLEAR")).upper()
        if label not in {"IN_SCOPE", "OUT_OF_SCOPE", "UNCLEAR"}:
            label = "UNCLEAR"
        try:
            confidence = max(0.0, min(1.0, float(payload.get("confidence", 0.0))))
        except (TypeError, ValueError):
            confidence = 0.0
        iit_signal = payload.get("iit_signal", False) is True
        return DomainClassification(label, confidence, iit_signal)
