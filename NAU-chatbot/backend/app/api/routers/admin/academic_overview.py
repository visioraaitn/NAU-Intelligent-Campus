from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import enforce_admin_rate_limit, require_admin
from app.domain.academic.enums import FormationElementType
from app.infrastructure.db import get_session
from app.models.schemas.admin import AcademicOverviewResponse
from app.repositories.academic import AcademicRepository, PageRequest
from app.services.academic.catalog_service import (
    AcademicCatalogService,
    FormationCatalogSnapshot,
)
from app.services.academic.element_resolution import AcademicElementResolutionService
from app.services.academic.tariff_resolution import AcademicTariffResolutionService
from app.services.rag.document_builder import AcademicDocumentBuilder


router = APIRouter(
    prefix="/admin/academic-overview",
    tags=["admin:academic-overview"],
    dependencies=[Depends(require_admin), Depends(enforce_admin_rate_limit)],
)

EntityT = TypeVar("EntityT")
ADMIN_ONLY_ELEMENT_TYPES = {
    FormationElementType.DOCUMENT_INSCRIPTION,
    FormationElementType.LIEN_PREINSCRIPTION,
}


@router.get("", response_model=AcademicOverviewResponse)
async def academic_overview(
    include_inactive: bool = Query(default=False),
    formation_id: int | None = Query(default=None, gt=0),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    catalogue = AcademicCatalogService(session)
    element_resolution = AcademicElementResolutionService(catalogue.elements)
    tariff_resolution = AcademicTariffResolutionService(catalogue.tarifs)
    builder = AcademicDocumentBuilder()
    request = PageRequest(page_size=100, include_inactive=include_inactive)
    if formation_id is None:
        parcours = await _collect(catalogue.parcours, request=request)
        formations = await _collect(catalogue.formations, request=request)
    else:
        formation = await catalogue.formations.require(
            formation_id,
            include_inactive=include_inactive,
        )
        current_parcours = await catalogue.parcours.require(
            formation.parcours_id,
            include_inactive=include_inactive,
        )
        parcours = [current_parcours]
        formations = [formation]
    parcours_by_id = {item.id: item for item in parcours}

    grouped: list[dict[str, object]] = []
    for formation in formations:
        current_parcours = parcours_by_id.get(formation.parcours_id)
        if current_parcours is None:
            continue
        filters = {"formation_id": formation.id}
        specialisations = await _collect(
            catalogue.specialisations,
            request=request,
            filters=filters,
        )
        elements = await _collect(catalogue.elements, request=request, filters=filters)
        effective_elements = await element_resolution.resolve_effective_elements(
            current_parcours.id,
            formation.id,
            include_inactive=include_inactive,
        )
        tarifs = await _collect(catalogue.tarifs, request=request, filters=filters)
        effective_tarifs = [
            await tariff_resolution.resolve_effective_tarif(
                parcours_id=current_parcours.id,
                formation_id=formation.id,
                specialisation_id=scope_specialisation_id,
                langue_enseignement=language,
                include_inactive=include_inactive,
            )
            for scope_specialisation_id in (
                None,
                *(item.id for item in specialisations),
            )
            for language in formation.langues_enseignement
        ]
        orientation_rules = await _collect(
            catalogue.orientation_rules,
            request=request,
            filters=filters,
        )
        accreditations = await _collect(
            catalogue.accreditations,
            request=request,
            filters=filters,
        )
        snapshot = FormationCatalogSnapshot(
            formation=formation,
            specialisations=tuple(specialisations),
            elements=tuple(
                element
                for element in elements
                if element.type_element not in ADMIN_ONLY_ELEMENT_TYPES
            ),
            tarifs=tuple(tarifs),
            orientation_rules=tuple(orientation_rules),
            accreditations=tuple(accreditations),
        )
        documents = builder.build_snapshot(snapshot) if formation.actif else []
        grouped.append(
            {
                "parcours": current_parcours,
                "formation": formation,
                "specialisations": specialisations,
                "elements": elements,
                "effective_elements": [
                    {"element": item.element, "scope": item.scope.value}
                    for item in effective_elements
                ],
                "tarifs": tarifs,
                "effective_tarifs": effective_tarifs,
                "orientation_rules": orientation_rules,
                "accreditations": accreditations,
                "rag_documents": [
                    {
                        "document_id": document.id,
                        "content": document.content,
                        "metadata": document.metadata,
                    }
                    for document in documents
                ],
            }
        )

    global_elements = await _collect(
        catalogue.elements,
        request=request,
        filters={
            "parcours_id": None,
            "formation_id": None,
            "specialisation_id": None,
        },
    )
    global_documents = [
        builder.element(element, None, None)
        for element in global_elements
        if element.actif and element.type_element not in ADMIN_ONLY_ELEMENT_TYPES
    ]
    return {
        "formations": grouped,
        "global_elements": global_elements,
        "global_rag_documents": [
            {
                "document_id": document.id,
                "content": document.content,
                "metadata": document.metadata,
            }
            for document in global_documents
        ],
    }


async def _collect(
    repository: AcademicRepository[EntityT],
    *,
    request: PageRequest,
    filters: Mapping[str, object] | None = None,
) -> list[EntityT]:
    items: list[EntityT] = []
    page = 1
    while True:
        response = await repository.list(
            PageRequest(
                page=page,
                page_size=request.page_size,
                include_inactive=request.include_inactive,
                filters=filters or {},
            )
        )
        items.extend(response.items)
        if page >= response.pages:
            return items
        page += 1
