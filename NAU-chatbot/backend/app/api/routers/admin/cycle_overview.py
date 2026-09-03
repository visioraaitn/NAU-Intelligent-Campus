from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import enforce_admin_rate_limit, require_admin
from app.infrastructure.db import get_session
from app.models.schemas.admin import AcademicCycleOverviewResponse
from app.repositories.academic import PageRequest
from app.services.academic import AcademicCatalogService, AcademicElementResolutionService


router = APIRouter(
    prefix="/admin/cycle-overview",
    tags=["admin:cycle-overview"],
    dependencies=[Depends(require_admin), Depends(enforce_admin_rate_limit)],
)


@router.get("", response_model=AcademicCycleOverviewResponse)
async def cycle_overview(
    parcours_id: int = Query(gt=0),
    include_inactive: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    catalogue = AcademicCatalogService(session)
    parcours = await catalogue.parcours.require(
        parcours_id,
        include_inactive=include_inactive,
    )
    formations = await catalogue.formations.list(
        PageRequest(
            page_size=100,
            include_inactive=include_inactive,
            filters={"parcours_id": parcours_id},
        )
    )
    tarifs = await catalogue.tarifs.list(
        PageRequest(
            page_size=100,
            include_inactive=include_inactive,
            filters={"parcours_id": parcours_id},
        )
    )
    effective_elements = await AcademicElementResolutionService(
        catalogue.elements
    ).resolve_effective_elements(
        parcours_id,
        include_inactive=include_inactive,
    )
    return {
        "parcours": parcours,
        "formations": formations.items,
        "effective_elements": [
            {"element": item.element, "scope": item.scope.value}
            for item in effective_elements
        ],
        "tarifs": tarifs.items,
    }
