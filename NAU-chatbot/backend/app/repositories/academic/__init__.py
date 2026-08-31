from app.repositories.academic.accreditations import AccreditationRepository
from app.repositories.academic.base import AcademicRepository, Page, PageRequest
from app.repositories.academic.elements import FormationElementRepository
from app.repositories.academic.formations import FormationRepository
from app.repositories.academic.orientation_rules import OrientationRuleRepository
from app.repositories.academic.parcours import ParcoursRepository
from app.repositories.academic.specialisations import SpecialisationRepository
from app.repositories.academic.tarifs import TarifRepository

__all__ = [
    "AcademicRepository",
    "AccreditationRepository",
    "FormationElementRepository",
    "FormationRepository",
    "OrientationRuleRepository",
    "Page",
    "PageRequest",
    "ParcoursRepository",
    "SpecialisationRepository",
    "TarifRepository",
]
