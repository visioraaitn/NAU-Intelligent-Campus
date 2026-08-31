from app.api.routers.admin.crud_factory import build_crud_router
from app.domain.academic.events import AcademicEntityType
from app.models.schemas.academic import ParcoursCreate, ParcoursRead, ParcoursUpdate


router = build_crud_router(
    path="parcours",
    tag="parcours",
    entity_type=AcademicEntityType.PARCOURS,
    create_schema=ParcoursCreate,
    update_schema=ParcoursUpdate,
    read_schema=ParcoursRead,
)
