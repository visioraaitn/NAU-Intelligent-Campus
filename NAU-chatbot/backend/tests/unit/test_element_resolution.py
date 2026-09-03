from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.domain.academic.enums import FormationElementType
from app.models.sqlalchemy import FormationElement
from app.services.academic.element_resolution import (
    AcademicElementResolutionService,
    ElementScope,
    resolve_element_precedence,
)


pytestmark = pytest.mark.unit


def _element(
    element_id: int,
    *,
    code: str,
    parcours_id: int | None = None,
    formation_id: int | None = None,
    specialisation_id: int | None = None,
) -> FormationElement:
    return FormationElement(
        id=element_id,
        parcours_id=parcours_id,
        formation_id=formation_id,
        specialisation_id=specialisation_id,
        type_element=FormationElementType.INFORMATION,
        code=code,
        nom="Pièces d’inscription",
        actif=True,
    )


async def test_parcours_information_is_resolved_for_its_formation() -> None:
    inherited = _element(1, code="INFO_PIECES", parcours_id=3)
    repository = AsyncMock()
    repository.list_applicable.return_value = [inherited]
    service = AcademicElementResolutionService(repository)

    result = await service.resolve_effective_elements(3, formation_id=30)

    repository.list_applicable.assert_awaited_once_with(
        parcours_id=3,
        formation_id=30,
        specialisation_id=None,
        element_types=None,
        include_inactive=False,
    )
    assert [(item.element.id, item.scope) for item in result] == [
        (1, ElementScope.PARCOURS)
    ]


def test_formation_information_overrides_same_parcours_information() -> None:
    inherited = _element(1, code="INFO_PIECES", parcours_id=3)
    specific = _element(2, code="INFO_PIECES", formation_id=30)

    result = resolve_element_precedence([specific, inherited])

    assert len(result) == 1
    assert result[0].element is specific
    assert result[0].scope is ElementScope.FORMATION


def test_formation_information_is_added_to_different_parcours_information() -> None:
    inherited = _element(1, code="DOC_CIN", parcours_id=3)
    specific = _element(2, code="DOC_ATTESTATION", formation_id=30)

    result = resolve_element_precedence([specific, inherited])

    assert {item.element.code for item in result} == {"DOC_CIN", "DOC_ATTESTATION"}
    assert {item.scope for item in result} == {
        ElementScope.PARCOURS,
        ElementScope.FORMATION,
    }


def test_specialisation_has_highest_precedence() -> None:
    global_element = _element(1, code="INFO_CONTACT")
    parcours_element = _element(2, code="INFO_CONTACT", parcours_id=3)
    formation_element = _element(3, code="INFO_CONTACT", formation_id=30)
    specialisation_element = _element(
        4,
        code="INFO_CONTACT",
        formation_id=30,
        specialisation_id=301,
    )

    result = resolve_element_precedence(
        [specialisation_element, global_element, formation_element, parcours_element]
    )

    assert len(result) == 1
    assert result[0].element is specialisation_element
    assert result[0].scope is ElementScope.SPECIALISATION
