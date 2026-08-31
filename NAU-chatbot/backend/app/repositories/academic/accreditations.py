from __future__ import annotations

from sqlalchemy import Select

from app.models.sqlalchemy import Accreditation, Formation, Parcours
from app.repositories.academic.base import AcademicRepository


class AccreditationRepository(AcademicRepository[Accreditation]):
    model = Accreditation
    resource_name = "accreditation"
    writable_fields = frozenset(
        {
            "formation_id",
            "code",
            "nom",
            "organisme",
            "description",
            "date_debut",
            "date_fin",
            "source_ref",
            "actif",
        }
    )
    filter_fields = {
        "formation_id": Accreditation.formation_id,
        "code": Accreditation.code,
        "organisme": Accreditation.organisme,
        "actif": Accreditation.actif,
    }
    search_fields = (
        Accreditation.code,
        Accreditation.nom,
        Accreditation.organisme,
        Accreditation.description,
        Accreditation.source_ref,
    )
    order_by = (Accreditation.nom.asc(), Accreditation.id.asc())

    def _apply_scope(
        self,
        statement: Select[object],
        *,
        include_inactive: bool,
    ) -> Select[object]:
        if include_inactive:
            return statement
        return (
            statement.join(Formation, Accreditation.formation_id == Formation.id)
            .join(Parcours, Formation.parcours_id == Parcours.id)
            .where(
                Accreditation.actif.is_(True),
                Formation.actif.is_(True),
                Parcours.actif.is_(True),
            )
        )

