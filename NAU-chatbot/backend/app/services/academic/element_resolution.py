from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from unicodedata import normalize

from app.domain.academic.enums import FormationElementType
from app.models.sqlalchemy import FormationElement
from app.repositories.academic import FormationElementRepository


class ElementScope(StrEnum):
    GLOBAL = "GLOBAL"
    PARCOURS = "PARCOURS"
    FORMATION = "FORMATION"
    SPECIALISATION = "SPECIALISATION"


@dataclass(frozen=True, slots=True)
class EffectiveFormationElement:
    element: FormationElement
    scope: ElementScope


class AcademicElementResolutionService:
    """Resolve applicable academic facts from broadest to most specific scope."""

    def __init__(self, repository: FormationElementRepository) -> None:
        self.repository = repository

    async def resolve_effective_elements(
        self,
        parcours_id: int,
        formation_id: int | None = None,
        specialisation_id: int | None = None,
        types: tuple[FormationElementType, ...] | None = None,
        *,
        include_inactive: bool = False,
    ) -> list[EffectiveFormationElement]:
        elements = await self.repository.list_applicable(
            parcours_id=parcours_id,
            formation_id=formation_id,
            specialisation_id=specialisation_id,
            element_types=types,
            include_inactive=include_inactive,
        )
        return resolve_element_precedence(elements)


def resolve_element_precedence(
    elements: list[FormationElement],
) -> list[EffectiveFormationElement]:
    resolved: dict[tuple[str, str], EffectiveFormationElement] = {}
    for element in sorted(elements, key=lambda item: _SCOPE_PRIORITY[_scope(item)]):
        resolved[_identity(element)] = EffectiveFormationElement(element, _scope(element))
    return sorted(
        resolved.values(),
        key=lambda item: (
            item.element.type_element.value,
            item.element.ordre_affichage is None,
            item.element.ordre_affichage or 0,
            item.element.nom.casefold(),
            item.element.id,
        ),
    )


def _identity(element: FormationElement) -> tuple[str, str]:
    identifier = element.code or normalize("NFKD", element.nom).encode("ascii", "ignore").decode().casefold()
    return element.type_element.value, identifier


def _scope(element: FormationElement) -> ElementScope:
    if element.specialisation_id is not None:
        return ElementScope.SPECIALISATION
    if element.formation_id is not None:
        return ElementScope.FORMATION
    if element.parcours_id is not None:
        return ElementScope.PARCOURS
    return ElementScope.GLOBAL


_SCOPE_PRIORITY = {
    ElementScope.GLOBAL: 0,
    ElementScope.PARCOURS: 1,
    ElementScope.FORMATION: 2,
    ElementScope.SPECIALISATION: 3,
}
