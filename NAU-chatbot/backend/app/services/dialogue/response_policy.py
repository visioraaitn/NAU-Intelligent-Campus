from __future__ import annotations

from collections.abc import Sequence

from app.services.dialogue.dialogue_act_detector import DialogueAct


def response_mode(intents: Sequence[str], act: DialogueAct) -> str:
    if act in {DialogueAct.REQUEST_MORE_DETAILS} or "DETAILS" in intents:
        return "DETAIL"
    if "ORIENTATION" in intents:
        return "RECOMMENDATION"
    return "FACT"


def focus_topics(intents: Sequence[str]) -> list[str]:
    return [intent for intent in intents if intent != "GENERAL"][:8]

