"""Academic-domain primitives."""

from app.domain.academic.enums import FormationElementType, OrientationRuleType, TarifStatus
from app.domain.academic.events import AcademicChangeAction, AcademicEntityType

__all__ = [
    "AcademicChangeAction",
    "AcademicEntityType",
    "FormationElementType",
    "OrientationRuleType",
    "TarifStatus",
]
