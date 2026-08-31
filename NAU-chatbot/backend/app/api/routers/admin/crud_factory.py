from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query, status
from pydantic import BaseModel

from app.core.dependencies import (
    admin_service,
    enforce_admin_rate_limit,
    require_admin,
)
from app.domain.academic.enums import FormationElementType
from app.domain.academic.events import AcademicEntityType
from app.models.schemas.academic import AcademicPage
from app.models.schemas.admin import MutationResponse
from app.repositories.academic import PageRequest
from app.services.admin.academic_service import AcademicAdminService


def build_crud_router(
    *,
    path: str,
    tag: str,
    entity_type: AcademicEntityType,
    create_schema: type[BaseModel],
    update_schema: type[BaseModel],
    read_schema: type[BaseModel],
) -> APIRouter:
    router = APIRouter(
        prefix=f"/admin/{path}",
        tags=[f"admin:{tag}"],
        dependencies=[Depends(require_admin), Depends(enforce_admin_rate_limit)],
    )
    page_response = AcademicPage[read_schema]
    mutation_response = MutationResponse[read_schema]

    @router.get("", response_model=page_response)
    async def list_entities(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        search: str | None = Query(default=None, max_length=200),
        include_inactive: bool = Query(default=False),
        actif: bool | None = Query(default=None),
        parcours_id: int | None = Query(default=None, gt=0),
        formation_id: int | None = Query(default=None, gt=0),
        specialisation_id: int | None = Query(default=None, gt=0),
        parent_id: int | None = Query(default=None, gt=0),
        type_element: FormationElementType | None = Query(default=None),
        code: str | None = Query(default=None, min_length=1, max_length=120),
        type_regle: str | None = Query(default=None, min_length=1, max_length=50),
        annee_universitaire: str | None = Query(default=None, min_length=1, max_length=50),
        statut: str | None = Query(default=None, min_length=1, max_length=50),
        langue_enseignement: str | None = Query(default=None, min_length=2, max_length=50),
        devise: str | None = Query(default=None, min_length=3, max_length=10),
        organisme: str | None = Query(default=None, min_length=1, max_length=255),
        service: AcademicAdminService = Depends(admin_service),
    ) -> dict[str, Any]:
        filters = {
            key: value
            for key, value in {
                "actif": actif,
                "parcours_id": parcours_id,
                "formation_id": formation_id,
                "specialisation_id": specialisation_id,
                "parent_id": parent_id,
                "type_element": type_element,
                "code": code,
                "type_regle": type_regle,
                "annee_universitaire": annee_universitaire,
                "statut": statut,
                "langue_enseignement": (
                    langue_enseignement.strip().upper()
                    if langue_enseignement
                    else None
                ),
                "devise": devise,
                "organisme": organisme,
            }.items()
            if value is not None
        }
        # Keep only filters supported by this repository.
        supported = service.repository(entity_type).filter_fields
        filters = {key: value for key, value in filters.items() if key in supported}
        result = await service.list(
            entity_type,
            PageRequest(page, page_size, search, include_inactive, filters),
        )
        return {
            "items": [read_schema.model_validate(item).model_dump(mode="json") for item in result.items],
            "total": result.total,
            "limit": result.page_size,
            "offset": result.offset,
        }

    @router.get("/{entity_id}", response_model=read_schema)
    async def get_entity(
        entity_id: Annotated[int, Path(gt=0)],
        service: AcademicAdminService = Depends(admin_service),
    ) -> dict[str, Any]:
        return read_schema.model_validate(await service.get(entity_type, entity_id)).model_dump(mode="json")

    @router.post(
        "",
        status_code=status.HTTP_201_CREATED,
        response_model=mutation_response,
    )
    async def create_entity(
        payload: create_schema,  # type: ignore[valid-type]
        service: AcademicAdminService = Depends(admin_service),
    ) -> dict[str, Any]:
        result = await service.create(entity_type, payload.model_dump())
        return _mutation(result, read_schema)

    @router.patch("/{entity_id}", response_model=mutation_response)
    async def update_entity(
        entity_id: Annotated[int, Path(gt=0)],
        payload: update_schema,  # type: ignore[valid-type]
        service: AcademicAdminService = Depends(admin_service),
    ) -> dict[str, Any]:
        result = await service.update(
            entity_type,
            entity_id,
            payload.model_dump(exclude_unset=True),
        )
        return _mutation(result, read_schema)

    @router.post("/{entity_id}/activate", response_model=mutation_response)
    async def activate_entity(
        entity_id: Annotated[int, Path(gt=0)],
        service: AcademicAdminService = Depends(admin_service),
    ) -> dict[str, Any]:
        return _mutation(await service.activate(entity_type, entity_id), read_schema)

    @router.post("/{entity_id}/deactivate", response_model=mutation_response)
    async def deactivate_entity(
        entity_id: Annotated[int, Path(gt=0)],
        service: AcademicAdminService = Depends(admin_service),
    ) -> dict[str, Any]:
        return _mutation(await service.deactivate(entity_type, entity_id), read_schema)

    @router.delete("/{entity_id}", response_model=mutation_response)
    async def delete_entity(
        entity_id: Annotated[int, Path(gt=0)],
        service: AcademicAdminService = Depends(admin_service),
    ) -> dict[str, Any]:
        return _mutation(await service.delete(entity_type, entity_id), read_schema)

    return router


def _mutation(result: Any, read_schema: type[BaseModel]) -> dict[str, Any]:
    return {
        "entity": read_schema.model_validate(result.entity).model_dump(mode="json") if result.entity is not None else None,
        "action": result.action.value,
        "indexing_status": result.indexing_status.value,
        "event_ids": [str(event.event_id) for event in result.events],
    }
