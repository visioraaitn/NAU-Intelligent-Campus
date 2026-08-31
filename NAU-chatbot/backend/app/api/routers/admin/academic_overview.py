from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import enforce_admin_rate_limit, require_admin
from app.infrastructure.db import get_session
from app.models.schemas.admin import AcademicOverviewResponse
from app.repositories.academic import AcademicRepository, PageRequest
from app.services.academic.catalog_service import (
    AcademicCatalogService,
    FormationCatalogSnapshot,
)
from app.services.rag.document_builder import AcademicDocumentBuilder


router = APIRouter(
    prefix="/admin/academic-overview",
    tags=["admin:academic-overview"],
    dependencies=[Depends(require_admin), Depends(enforce_admin_rate_limit)],
)

EntityT = TypeVar("EntityT")


@router.get("", response_model=AcademicOverviewResponse)
async def academic_overview(
    include_inactive: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    catalogue = AcademicCatalogService(session)
    builder = AcademicDocumentBuilder()
    request = PageRequest(page_size=100, include_inactive=include_inactive)
    parcours = await _collect(catalogue.parcours, request=request)
    formations = await _collect(catalogue.formations, request=request)
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
        tarifs = await _collect(catalogue.tarifs, request=request, filters=filters)
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
            elements=tuple(elements),
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
                "tarifs": tarifs,
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
        filters={"formation_id": None},
    )
    global_documents = [
        builder.element(element, None, None)
        for element in global_elements
        if element.actif
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
