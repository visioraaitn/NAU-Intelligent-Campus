from app.api.routers.admin.accreditations import router as accreditations_router
from app.api.routers.admin.academic_overview import router as academic_overview_router
from app.api.routers.admin.cycle_overview import router as cycle_overview_router
from app.api.routers.admin.elements import router as elements_router
from app.api.routers.admin.formations import router as formations_router
from app.api.routers.admin.orientation_rules import router as orientation_rules_router
from app.api.routers.admin.orientation_matrix import router as orientation_matrix_router
from app.api.routers.admin.parcours import router as parcours_router
from app.api.routers.admin.rag import router as rag_router
from app.api.routers.admin.specialisations import router as specialisations_router
from app.api.routers.admin.tarifs import router as tarifs_router

__all__ = [
    "accreditations_router", "academic_overview_router", "cycle_overview_router", "elements_router", "formations_router",
    "orientation_matrix_router", "orientation_rules_router", "parcours_router", "rag_router",
    "specialisations_router", "tarifs_router",
]
