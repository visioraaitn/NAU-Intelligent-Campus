from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.core.file_config import prompt_text
from app.services.llm.providers import LLMMessage, LLMProvider


@dataclass(frozen=True, slots=True)
class DomainClassification:
    label: str
    confidence: float
    iit_signal: bool = False


class EspritNluService:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

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

