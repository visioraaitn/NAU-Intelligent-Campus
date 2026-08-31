from __future__ import annotations

from sqlalchemy import Select, func, select

from app.models.sqlalchemy import (
    Accreditation,
    Formation,
    FormationElement,
    Parcours,
    RegleOrientation,
    Specialisation,
    Tarif,
)
from app.repositories.academic.base import AcademicRepository


class FormationRepository(AcademicRepository[Formation]):
    model = Formation
    resource_name = "formation"
    writable_fields = frozenset(
        {
            "parcours_id",
            "code",
            "nom",
            "intitule_diplome",
            "duree_annees",
            "nb_semestres",
            "credits_total",
            "langues_enseignement",
            "description",
            "source_ref",
            "actif",
        }
    )
    filter_fields = {
        "parcours_id": Formation.parcours_id,
        "code": Formation.code,
        "duree_annees": Formation.duree_annees,
        "actif": Formation.actif,
    }
    search_fields = (
        Formation.code,
        Formation.nom,
        Formation.intitule_diplome,
        Formation.description,
        Formation.source_ref,
    )
    order_by = (Formation.nom.asc(), Formation.id.asc())

    def _apply_scope(
        self,
        statement: Select[object],
        *,
        include_inactive: bool,
    ) -> Select[object]:
        if include_inactive:
            return statement
        return statement.join(Parcours, Formation.parcours_id == Parcours.id).where(
            Formation.actif.is_(True),
            Parcours.actif.is_(True),
        )

    async def dependency_counts(self, entity_id: int) -> dict[str, int]:
        statement = select(
            select(func.count(Specialisation.id))
            .where(Specialisation.formation_id == entity_id)
            .scalar_subquery()
            .label("specialisations"),
            select(func.count(FormationElement.id))
            .where(FormationElement.formation_id == entity_id)
            .scalar_subquery()
            .label("elements"),
            select(func.count(Tarif.id))
            .where(Tarif.formation_id == entity_id)
            .scalar_subquery()
            .label("tarifs"),
            select(func.count(RegleOrientation.id))
            .where(RegleOrientation.formation_id == entity_id)
            .scalar_subquery()
            .label("orientation_rules"),
            select(func.count(Accreditation.id))
            .where(Accreditation.formation_id == entity_id)
            .scalar_subquery()
            .label("accreditations"),
        )
        row = (await self.session.execute(statement)).one()
        return {name: int(value) for name, value in row._mapping.items() if value}
