from __future__ import annotations

from sqlalchemy import Select, func, select

from app.models.sqlalchemy import (
    Formation,
    FormationElement,
    Parcours,
    RegleOrientation,
    Specialisation,
    Tarif,
)
from app.repositories.academic.base import AcademicRepository


class SpecialisationRepository(AcademicRepository[Specialisation]):
    model = Specialisation
    resource_name = "specialisation"
    writable_fields = frozenset(
        {
            "formation_id",
            "code",
            "nom",
            "description",
            "ordre_affichage",
            "source_ref",
            "actif",
        }
    )
    filter_fields = {
        "formation_id": Specialisation.formation_id,
        "code": Specialisation.code,
        "actif": Specialisation.actif,
    }
    search_fields = (
        Specialisation.code,
        Specialisation.nom,
        Specialisation.description,
        Specialisation.source_ref,
    )
    order_by = (
        Specialisation.ordre_affichage.asc().nullslast(),
        Specialisation.nom.asc(),
        Specialisation.id.asc(),
    )

    def _apply_scope(
        self,
        statement: Select[object],
        *,
        include_inactive: bool,
    ) -> Select[object]:
        if include_inactive:
            return statement
        return (
            statement.join(Formation, Specialisation.formation_id == Formation.id)
            .join(Parcours, Formation.parcours_id == Parcours.id)
            .where(
                Specialisation.actif.is_(True),
                Formation.actif.is_(True),
                Parcours.actif.is_(True),
            )
        )

    async def dependency_counts(self, entity_id: int) -> dict[str, int]:
        statement = select(
            select(func.count(FormationElement.id))
            .where(FormationElement.specialisation_id == entity_id)
            .scalar_subquery()
            .label("elements"),
            select(func.count(Tarif.id))
            .where(Tarif.specialisation_id == entity_id)
            .scalar_subquery()
            .label("tarifs"),
            select(func.count(RegleOrientation.id))
            .where(RegleOrientation.specialisation_id == entity_id)
            .scalar_subquery()
            .label("orientation_rules"),
        )
        row = (await self.session.execute(statement)).one()
        return {name: int(value) for name, value in row._mapping.items() if value}

