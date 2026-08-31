from __future__ import annotations

import logging
from collections.abc import Sequence

from app.domain.conversation.models import SubjectState
from app.services.dialogue.human_labels import intent_label, profile_label, value_label


logger = logging.getLogger("iit.chat")


def log_stage(event: str, *, session_id: str, **fields: object) -> None:
    safe = {key: value for key, value in fields.items() if value is not None}
    logger.info(event, extra={"session_id": session_id, "event_fields": safe})


def readable_summary(subject: SubjectState, intents: Sequence[str]) -> str:
    return (
        f"Situation : {profile_label(subject.profile)}; "
        f"section du bac : {value_label(subject.bac_specialty) if subject.bac_specialty else 'non précisée'}; "
        f"spécialité de licence : {value_label(subject.licence_specialty) if subject.licence_specialty else 'non précisée'}; "
        f"demande : {', '.join(intent_label(item) for item in intents) or 'non précisée'}; "
        f"formation déjà proposée : {value_label(subject.recommended_offer) if subject.recommended_offer else 'aucune'}"
    )
