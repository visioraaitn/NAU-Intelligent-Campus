from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.sqlalchemy import (
    Accreditation,
    Formation,
    FormationElement,
    Parcours,
    RegleOrientation,
    Specialisation,
    Tarif,
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


ItemT = TypeVar("ItemT")
CATALOG_PAGE_SIZE = 100
MAX_SNAPSHOT_ITEMS_PER_ENTITY = 1_000


@dataclass(frozen=True, slots=True)
class FormationCatalogSnapshot:
    formation: Formation
    specialisations: tuple[Specialisation, ...]
    elements: tuple[FormationElement, ...]
    tarifs: tuple[Tarif, ...]
    orientation_rules: tuple[RegleOrientation, ...]
    accreditations: tuple[Accreditation, ...]


class AcademicCatalogService:
    """Read-only, active-by-default access to PostgreSQL academic truth."""

    def __init__(self, session: AsyncSession) -> None:
        self.parcours = ParcoursRepository(session)
        self.formations = FormationRepository(session)
        self.specialisations = SpecialisationRepository(session)
        self.elements = FormationElementRepository(session)
        self.tarifs = TarifRepository(session)
        self.orientation_rules = OrientationRuleRepository(session)
        self.accreditations = AccreditationRepository(session)

    async def list_parcours(self, request: PageRequest | None = None) -> Page[Parcours]:
        return await self.parcours.list(request)

    async def list_formations(
        self,
        request: PageRequest | None = None,
        *,
        parcours_id: int | None = None,
    ) -> Page[Formation]:
        return await self.formations.list(
            _with_filter(request, "parcours_id", parcours_id)
            if parcours_id is not None
            else request
        )

    async def get_formation(self, formation_id: int) -> Formation:
        return await self.formations.require(formation_id)

    async def get_formation_by_code(self, code: str) -> Formation:
        formation = await self.formations.get_by_code(code)
        if formation is None:
            raise NotFoundError("formation", code)
        return formation

    async def list_specialisations(
        self,
        formation_id: int,
        request: PageRequest | None = None,
    ) -> Page[Specialisation]:
        return await self.specialisations.list(
            _with_filter(request, "formation_id", formation_id)
        )

    async def list_elements(
        self,
        request: PageRequest | None = None,
        *,
        formation_id: int | None = None,
        specialisation_id: int | None = None,
        element_type: object | None = None,
    ) -> Page[FormationElement]:
        query = request
        if formation_id is not None:
            query = _with_filter(query, "formation_id", formation_id)
        if specialisation_id is not None:
            query = _with_filter(query, "specialisation_id", specialisation_id)
        if element_type is not None:
            query = _with_filter(query, "type_element", element_type)
        return await self.elements.list(query)

    async def list_tarifs(
        self,
        formation_id: int,
        request: PageRequest | None = None,
        *,
        specialisation_id: int | None = None,
    ) -> Page[Tarif]:
        query = _with_filter(request, "formation_id", formation_id)
        if specialisation_id is not None:
            query = _with_filter(query, "specialisation_id", specialisation_id)
        return await self.tarifs.list(query)

    async def list_orientation_rules(
        self,
        formation_id: int,
        request: PageRequest | None = None,
        *,
        specialisation_id: int | None = None,
    ) -> Page[RegleOrientation]:
        query = _with_filter(request, "formation_id", formation_id)
        if specialisation_id is not None:
            query = _with_filter(query, "specialisation_id", specialisation_id)
        return await self.orientation_rules.list(query)

    async def list_accreditations(
        self,
        formation_id: int,
        request: PageRequest | None = None,
    ) -> Page[Accreditation]:
        return await self.accreditations.list(
            _with_filter(request, "formation_id", formation_id)
        )

    async def formation_snapshot(self, formation_id: int) -> FormationCatalogSnapshot:
        """Load a bounded complete snapshot for recommendation/RAG consumers."""

        formation = await self.get_formation(formation_id)
        return FormationCatalogSnapshot(
            formation=formation,
            specialisations=tuple(
                await _collect(self.specialisations, {"formation_id": formation_id})
            ),
            elements=tuple(await _collect(self.elements, {"formation_id": formation_id})),
            tarifs=tuple(await _collect(self.tarifs, {"formation_id": formation_id})),
            orientation_rules=tuple(
                await _collect(self.orientation_rules, {"formation_id": formation_id})
            ),
            accreditations=tuple(
                await _collect(self.accreditations, {"formation_id": formation_id})
            ),
        )


def _with_filter(
    request: PageRequest | None,
    name: str,
    value: object,
) -> PageRequest:
    query = request or PageRequest()
    filters = dict(query.filters)
    existing = filters.get(name)
    if name in filters and existing != value:
        raise ValueError(f"filter {name} conflicts with the requested catalogue scope")
    filters[name] = value
    return replace(query, filters=filters)


async def _collect(
    repository: AcademicRepository[ItemT],
    filters: dict[str, object],
) -> list[ItemT]:
    items: list[ItemT] = []
    page_number = 1
    while len(items) < MAX_SNAPSHOT_ITEMS_PER_ENTITY:
        page = await repository.list(
            PageRequest(
                page=page_number,
                page_size=CATALOG_PAGE_SIZE,
                filters=filters,
            )
        )
        items.extend(page.items)
        if page_number >= page.pages:
            return items
        page_number += 1
    raise RuntimeError("academic snapshot exceeds its configured safety bound")

