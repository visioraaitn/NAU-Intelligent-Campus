from __future__ import annotations

from sqlalchemy import Select, or_

from app.models.sqlalchemy import Formation, Parcours, RegleOrientation, Specialisation
from app.repositories.academic.base import AcademicRepository


class OrientationRuleRepository(AcademicRepository[RegleOrientation]):
    model = RegleOrientation
    resource_name = "regle d'orientation"
    writable_fields = frozenset(
        {
            "formation_id",
            "specialisation_id",
            "code",
            "nom",
            "type_regle",
            "criteres",
            "description",
            "priorite",
            "source_ref",
            "actif",
        }
    )
    filter_fields = {
        "formation_id": RegleOrientation.formation_id,
        "specialisation_id": RegleOrientation.specialisation_id,
        "code": RegleOrientation.code,
        "type_regle": RegleOrientation.type_regle,
        "priorite": RegleOrientation.priorite,
        "actif": RegleOrientation.actif,
    }
    search_fields = (
        RegleOrientation.code,
        RegleOrientation.nom,
        RegleOrientation.type_regle,
        RegleOrientation.description,
        RegleOrientation.source_ref,
    )
    order_by = (RegleOrientation.priorite.desc(), RegleOrientation.id.asc())

    def _apply_scope(
        self,
        statement: Select[object],
        *,
        include_inactive: bool,
    ) -> Select[object]:
        if include_inactive:
            return statement
        return (
            statement.join(Formation, RegleOrientation.formation_id == Formation.id)
            .join(Parcours, Formation.parcours_id == Parcours.id)
            .outerjoin(
                Specialisation,
                RegleOrientation.specialisation_id == Specialisation.id,
            )
            .where(
                RegleOrientation.actif.is_(True),
                Formation.actif.is_(True),
                Parcours.actif.is_(True),
                or_(
                    RegleOrientation.specialisation_id.is_(None),
                    Specialisation.actif.is_(True),
                ),
            )
        )

