from app.api.routers.admin.crud_factory import build_crud_router
from app.domain.academic.events import AcademicEntityType
from app.models.schemas.academic import (
    FormationElementCreate,
    FormationElementRead,
    FormationElementUpdate,
)


router = build_crud_router(
    path="elements",
    tag="elements",
    entity_type=AcademicEntityType.FORMATION_ELEMENT,
    create_schema=FormationElementCreate,
    update_schema=FormationElementUpdate,
    read_schema=FormationElementRead,
)
