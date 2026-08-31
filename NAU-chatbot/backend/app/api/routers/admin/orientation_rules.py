from app.api.routers.admin.crud_factory import build_crud_router
from app.domain.academic.events import AcademicEntityType
from app.models.schemas.academic import (
    RegleOrientationCreate,
    RegleOrientationRead,
    RegleOrientationUpdate,
)


router = build_crud_router(
    path="orientation-rules",
    tag="orientation-rules",
    entity_type=AcademicEntityType.ORIENTATION_RULE,
    create_schema=RegleOrientationCreate,
    update_schema=RegleOrientationUpdate,
    read_schema=RegleOrientationRead,
)
