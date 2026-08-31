from app.api.routers.admin.crud_factory import build_crud_router
from app.domain.academic.events import AcademicEntityType
from app.models.schemas.academic import (
    AccreditationCreate,
    AccreditationRead,
    AccreditationUpdate,
)


router = build_crud_router(
    path="accreditations",
    tag="accreditations",
    entity_type=AcademicEntityType.ACCREDITATION,
    create_schema=AccreditationCreate,
    update_schema=AccreditationUpdate,
    read_schema=AccreditationRead,
)
