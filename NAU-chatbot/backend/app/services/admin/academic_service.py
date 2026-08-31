from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar, cast
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.domain.academic.events import (
    AcademicChangeAction,
    AcademicEntityChanged,
    AcademicEntityType,
    EventPublisher,
)
from app.repositories.academic import (
    AccreditationRepository,
    AcademicRepository,
    FormationElementRepository,
    FormationRepository,
    OrientationRuleRepository,
    Page,
    PageRequest,
    ParcoursRepository,
    SpecialisationRepository,
    TarifRepository,
)


logger = logging.getLogger(__name__)
EntityT = TypeVar("EntityT")


class IndexingStatus(str, Enum):
    QUEUED = "QUEUED"
    PUBLISH_FAILED = "PUBLISH_FAILED"


@dataclass(frozen=True, slots=True)
class AcademicMutationResult(Generic[EntityT]):
    entity_type: AcademicEntityType
    entity_id: int
    action: AcademicChangeAction
    entity: EntityT | None
    events: tuple[AcademicEntityChanged, ...]
    indexing_status: IndexingStatus
    failed_event_ids: tuple[UUID, ...] = ()


class AcademicAdminService:
    """Transaction owner for academic CRUD and post-commit RAG events."""

    _REPOSITORIES: dict[AcademicEntityType, type[AcademicRepository[Any]]] = {
        AcademicEntityType.PARCOURS: ParcoursRepository,
        AcademicEntityType.FORMATION: FormationRepository,
        AcademicEntityType.SPECIALISATION: SpecialisationRepository,
        AcademicEntityType.FORMATION_ELEMENT: FormationElementRepository,
        AcademicEntityType.TARIF: TarifRepository,
        AcademicEntityType.ORIENTATION_RULE: OrientationRuleRepository,
        AcademicEntityType.ACCREDITATION: AccreditationRepository,
    }

    def __init__(self, session: AsyncSession, event_publisher: EventPublisher) -> None:
        self.session = session
        self.event_publisher = event_publisher

    def repository(self, entity_type: AcademicEntityType) -> AcademicRepository[Any]:
        repository_type = self._REPOSITORIES[entity_type]
        return repository_type(self.session)

    async def list(
        self,
        entity_type: AcademicEntityType,
        request: PageRequest | None = None,
    ) -> Page[Any]:
        query = request or PageRequest(include_inactive=True)
        return await self.repository(entity_type).list(query)

    async def get(self, entity_type: AcademicEntityType, entity_id: int) -> Any:
        return await self.repository(entity_type).require(
            entity_id,
            include_inactive=True,
        )

    async def create(
        self,
        entity_type: AcademicEntityType,
        values: Mapping[str, Any],
    ) -> AcademicMutationResult[Any]:
        repository = self.repository(entity_type)
        try:
            async with self.session.begin():
                entity = await repository.create(values)
                entity_id = int(getattr(entity, "id"))
                formation_ids = await self._affected_formation_ids(entity_type, entity)
        except IntegrityError as exc:
            raise self._integrity_conflict(entity_type) from exc

        events = self._events(
            entity_type,
            entity_id,
            formation_ids,
            AcademicChangeAction.CREATED,
        )
        return await self._publish_result(entity_type, entity_id, entity, events)

    async def update(
        self,
        entity_type: AcademicEntityType,
        entity_id: int,
        values: Mapping[str, Any],
    ) -> AcademicMutationResult[Any]:
        repository = self.repository(entity_type)
        try:
            async with self.session.begin():
                entity = await repository.require(
                    entity_id,
                    include_inactive=True,
                    for_update=True,
                )
                was_active = bool(getattr(entity, "actif"))
                before = await self._affected_formation_ids(entity_type, entity)
                entity = await repository.update(entity, values)
                is_active = bool(getattr(entity, "actif"))
                after = await self._affected_formation_ids(entity_type, entity)
                formation_ids = _ordered_union(before, after)
        except IntegrityError as exc:
            raise self._integrity_conflict(entity_type) from exc

        action = AcademicChangeAction.UPDATED
        if was_active and not is_active:
            action = AcademicChangeAction.DEACTIVATED
        elif not was_active and is_active:
            action = AcademicChangeAction.ACTIVATED
        events = self._events(
            entity_type,
            entity_id,
            formation_ids,
            action,
        )
        return await self._publish_result(entity_type, entity_id, entity, events)

    async def activate(
        self,
        entity_type: AcademicEntityType,
        entity_id: int,
    ) -> AcademicMutationResult[Any]:
        return await self._set_active(entity_type, entity_id, True)

    async def deactivate(
        self,
        entity_type: AcademicEntityType,
        entity_id: int,
    ) -> AcademicMutationResult[Any]:
        return await self._set_active(entity_type, entity_id, False)

    async def _set_active(
        self,
        entity_type: AcademicEntityType,
        entity_id: int,
        active: bool,
    ) -> AcademicMutationResult[Any]:
        repository = self.repository(entity_type)
        try:
            async with self.session.begin():
                entity = await repository.require(
                    entity_id,
                    include_inactive=True,
                    for_update=True,
                )
                entity = await repository.set_active(entity, active)
                formation_ids = await self._affected_formation_ids(entity_type, entity)
        except IntegrityError as exc:
            raise self._integrity_conflict(entity_type) from exc

        action = (
            AcademicChangeAction.ACTIVATED
            if active
            else AcademicChangeAction.DEACTIVATED
        )
        events = self._events(entity_type, entity_id, formation_ids, action)
        return await self._publish_result(entity_type, entity_id, entity, events)

    async def delete(
        self,
        entity_type: AcademicEntityType,
        entity_id: int,
    ) -> AcademicMutationResult[Any]:
        repository = self.repository(entity_type)
        try:
            async with self.session.begin():
                entity = await repository.require(
                    entity_id,
                    include_inactive=True,
                    for_update=True,
                )
                dependencies = await repository.dependency_counts(entity_id)
                if dependencies:
                    raise ConflictError(
                        "Suppression refusee: des donnees academiques dependent encore de cette ressource. Desactivez-la plutot.",
                        details={
                            "entity_type": entity_type.value,
                            "entity_id": entity_id,
                            "dependencies": dependencies,
                        },
                    )
                formation_ids = await self._affected_formation_ids(entity_type, entity)
                await repository.delete(entity)
        except IntegrityError as exc:
            raise self._integrity_conflict(entity_type) from exc

        events = self._events(
            entity_type,
            entity_id,
            formation_ids,
            AcademicChangeAction.DELETED,
        )
        return await self._publish_result(entity_type, entity_id, None, events)

    async def _affected_formation_ids(
        self,
        entity_type: AcademicEntityType,
        entity: Any,
    ) -> tuple[int | None, ...]:
        if entity_type is AcademicEntityType.FORMATION:
            return (int(getattr(entity, "id")),)
        if entity_type is AcademicEntityType.PARCOURS:
            repository = cast(ParcoursRepository, self.repository(entity_type))
            ids = await repository.formation_ids(int(getattr(entity, "id")))
            return tuple(ids) or (None,)
        formation_id = getattr(entity, "formation_id", None)
        return (None if formation_id is None else int(formation_id),)

    @staticmethod
    def _events(
        entity_type: AcademicEntityType,
        entity_id: int,
        formation_ids: tuple[int | None, ...],
        action: AcademicChangeAction,
    ) -> tuple[AcademicEntityChanged, ...]:
        return tuple(
            AcademicEntityChanged(
                entity_type=entity_type,
                entity_id=entity_id,
                formation_id=formation_id,
                action=action,
            )
            for formation_id in formation_ids
        )

    async def _publish_result(
        self,
        entity_type: AcademicEntityType,
        entity_id: int,
        entity: EntityT | None,
        events: tuple[AcademicEntityChanged, ...],
    ) -> AcademicMutationResult[EntityT]:
        failed: list[UUID] = []
        for event in events:
            try:
                await self.event_publisher.publish(event)
            except Exception:  # The DB commit is authoritative and already complete.
                failed.append(event.event_id)
                logger.exception(
                    "ADMIN_CHANGE event publication failed",
                    extra={
                        "event_id": str(event.event_id),
                        "entity_type": event.entity_type.value,
                        "entity_id": event.entity_id,
                        "formation_id": event.formation_id,
                    },
                )
        action = events[0].action
        return AcademicMutationResult(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            entity=entity,
            events=events,
            indexing_status=(
                IndexingStatus.PUBLISH_FAILED if failed else IndexingStatus.QUEUED
            ),
            failed_event_ids=tuple(failed),
        )

    @staticmethod
    def _integrity_conflict(entity_type: AcademicEntityType) -> ConflictError:
        return ConflictError(
            "La modification viole une contrainte du catalogue academique.",
            details={"entity_type": entity_type.value},
        )


def _ordered_union(
    first: tuple[int | None, ...],
    second: tuple[int | None, ...],
) -> tuple[int | None, ...]:
    return tuple(dict.fromkeys((*first, *second)))
