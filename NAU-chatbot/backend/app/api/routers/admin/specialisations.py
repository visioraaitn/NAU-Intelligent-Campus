from app.api.routers.admin.crud_factory import build_crud_router
from app.domain.academic.events import AcademicEntityType
from app.models.schemas.academic import (
    SpecialisationCreate,
    SpecialisationRead,
    SpecialisationUpdate,
)


router = build_crud_router(
    path="specialisations",
    tag="specialisations",
    entity_type=AcademicEntityType.SPECIALISATION,
    create_schema=SpecialisationCreate,
    update_schema=SpecialisationUpdate,
    read_schema=SpecialisationRead,
)
