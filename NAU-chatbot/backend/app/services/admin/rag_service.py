from __future__ import annotations

from dataclasses import dataclass

from app.domain.academic.events import (
    AcademicChangeAction,
    AcademicEntityChanged,
    AcademicEntityType,
    EventPublisher,
)
from app.repositories.academic import (
    FormationRepository,
)
from app.services.rag.status_store import RagStatusStore


@dataclass(frozen=True, slots=True)
class RagQueueResult:
    events: tuple[AcademicEntityChanged, ...]

    @property
    def queued(self) -> int:
        return len(self.events)


class RagAdminService:
    """Queues reproducible indexing work without performing it in API workers."""

    def __init__(
        self,
        formations: FormationRepository,
        publisher: EventPublisher,
        status: RagStatusStore,
    ) -> None:
        self.formations = formations
        self.publisher = publisher
        self.status = status

    async def enqueue_formation(self, formation_id: int) -> RagQueueResult:
        formation = await self.formations.require(formation_id)
        event = AcademicEntityChanged(
            entity_type=AcademicEntityType.FORMATION,
            entity_id=formation.id,
            formation_id=formation.id,
            action=AcademicChangeAction.UPDATED,
        )
        await self.publisher.publish(event)
        return RagQueueResult((event,))

    async def enqueue_all(self) -> RagQueueResult:
        event = AcademicEntityChanged(
            entity_type=AcademicEntityType.CATALOGUE,
            entity_id=1,
            formation_id=None,
            action=AcademicChangeAction.UPDATED,
        )
        await self.publisher.publish(event)
        return RagQueueResult((event,))

    async def recent_status(self, limit: int) -> list[dict[str, object]]:
        return await self.status.recent(limit)
