from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4


class AcademicEntityType(str, Enum):
    CATALOGUE = "CATALOGUE"
    PARCOURS = "PARCOURS"
    FORMATION = "FORMATION"
    SPECIALISATION = "SPECIALISATION"
    FORMATION_ELEMENT = "FORMATION_ELEMENT"
    TARIF = "TARIF"
    ORIENTATION_RULE = "ORIENTATION_RULE"
    ACCREDITATION = "ACCREDITATION"


class AcademicChangeAction(str, Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    ACTIVATED = "ACTIVATED"
    DEACTIVATED = "DEACTIVATED"
    DELETED = "DELETED"


@dataclass(frozen=True, slots=True)
class AcademicEntityChanged:
    """Committed academic change consumed by the incremental RAG worker.

    ``formation_id`` is nullable only for a parcours change or a global
    formation element. Consumers must treat ``None`` as an explicitly broad or
    global invalidation; it is never inferred from untrusted queue data.
    """

    entity_type: AcademicEntityType
    entity_id: int
    formation_id: int | None
    action: AcademicChangeAction
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    attempt: int = 0

    def __post_init__(self) -> None:
        if self.entity_id <= 0:
            raise ValueError("entity_id must be positive")
        if self.formation_id is not None and self.formation_id <= 0:
            raise ValueError("formation_id must be positive when provided")
        if self.attempt < 0:
            raise ValueError("attempt cannot be negative")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")

    def to_payload(self) -> dict[str, str | int | None]:
        """Return a JSON-safe payload with stable field names."""

        return {
            "event_id": str(self.event_id),
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "formation_id": self.formation_id,
            "action": self.action.value,
            "occurred_at": self.occurred_at.astimezone(UTC).isoformat(),
            "attempt": self.attempt,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> AcademicEntityChanged:
        """Validate a deserialized queue payload at the worker boundary."""

        occurred_at = datetime.fromisoformat(str(payload["occurred_at"]).replace("Z", "+00:00"))
        raw_formation_id = payload.get("formation_id")
        return cls(
            event_id=UUID(str(payload["event_id"])),
            entity_type=AcademicEntityType(str(payload["entity_type"])),
            entity_id=int(payload["entity_id"]),
            formation_id=None if raw_formation_id is None else int(raw_formation_id),
            action=AcademicChangeAction(str(payload["action"])),
            occurred_at=occurred_at,
            attempt=int(payload.get("attempt", 0)),
        )

    def for_retry(self) -> AcademicEntityChanged:
        return AcademicEntityChanged(
            event_id=self.event_id,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            formation_id=self.formation_id,
            action=self.action,
            occurred_at=self.occurred_at,
            attempt=self.attempt + 1,
        )


@runtime_checkable
class EventPublisher(Protocol):
    async def publish(self, event: AcademicEntityChanged) -> None:
        """Publish an already-committed event or raise on failure."""
