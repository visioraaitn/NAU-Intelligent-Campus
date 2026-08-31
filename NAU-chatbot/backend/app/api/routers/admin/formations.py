from app.api.routers.admin.crud_factory import build_crud_router
from app.domain.academic.events import AcademicEntityType
from app.models.schemas.academic import FormationCreate, FormationRead, FormationUpdate


router = build_crud_router(
    path="formations",
    tag="formations",
    entity_type=AcademicEntityType.FORMATION,
    create_schema=FormationCreate,
    update_schema=FormationUpdate,
    read_schema=FormationRead,
)
