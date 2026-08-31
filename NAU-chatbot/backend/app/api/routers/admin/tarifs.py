from app.api.routers.admin.crud_factory import build_crud_router
from app.domain.academic.events import AcademicEntityType
from app.models.schemas.academic import TarifCreate, TarifRead, TarifUpdate


router = build_crud_router(
    path="tarifs",
    tag="tarifs",
    entity_type=AcademicEntityType.TARIF,
    create_schema=TarifCreate,
    update_schema=TarifUpdate,
    read_schema=TarifRead,
)
