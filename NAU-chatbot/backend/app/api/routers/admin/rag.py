from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.core.dependencies import (
    enforce_admin_rate_limit,
    rag_admin_service,
    require_admin,
)
from app.models.schemas.admin import RagQueueResponse, RagStatusResponse
from app.services.admin.rag_service import RagAdminService, RagQueueResult


router = APIRouter(
    prefix="/admin/rag",
    tags=["admin:rag"],
    dependencies=[Depends(require_admin), Depends(enforce_admin_rate_limit)],
)


def _queue_response(result: RagQueueResult) -> RagQueueResponse:
    return RagQueueResponse(
        queued=result.queued,
        event_ids=[event.event_id for event in result.events],
    )


@router.post(
    "/reindex",
    response_model=RagQueueResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reindex_all(
    service: RagAdminService = Depends(rag_admin_service),
) -> RagQueueResponse:
    return _queue_response(await service.enqueue_all())


@router.post(
    "/reindex/{formation_id}",
    response_model=RagQueueResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reindex_formation(
    formation_id: Annotated[int, Path(gt=0)],
    service: RagAdminService = Depends(rag_admin_service),
) -> RagQueueResponse:
    return _queue_response(await service.enqueue_formation(formation_id))


@router.get("/status", response_model=RagStatusResponse)
async def rag_status(
    limit: int = Query(default=50, ge=1, le=100),
    service: RagAdminService = Depends(rag_admin_service),
) -> RagStatusResponse:
    return RagStatusResponse(jobs=await service.recent_status(limit))
