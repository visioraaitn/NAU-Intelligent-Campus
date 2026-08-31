from __future__ import annotations

from sqlalchemy import Select, and_, func, or_, select

from app.models.sqlalchemy import Formation, FormationElement, Parcours, Specialisation
from app.repositories.academic.base import AcademicRepository


class FormationElementRepository(AcademicRepository[FormationElement]):
    model = FormationElement
    resource_name = "element de formation"
    writable_fields = frozenset(
        {
            "formation_id",
            "specialisation_id",
            "parent_id",
            "type_element",
            "code",
            "nom",
            "description",
            "organisme",
            "ordre_affichage",
            "source_ref",
            "actif",
        }
    )
    filter_fields = {
        "formation_id": FormationElement.formation_id,
        "specialisation_id": FormationElement.specialisation_id,
        "parent_id": FormationElement.parent_id,
        "type_element": FormationElement.type_element,
        "code": FormationElement.code,
        "actif": FormationElement.actif,
    }
    search_fields = (
        FormationElement.code,
        FormationElement.nom,
        FormationElement.description,
        FormationElement.organisme,
        FormationElement.source_ref,
    )
    order_by = (
        FormationElement.ordre_affichage.asc().nullslast(),
        FormationElement.nom.asc(),
        FormationElement.id.asc(),
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
            statement.outerjoin(Formation, FormationElement.formation_id == Formation.id)
            .outerjoin(Parcours, Formation.parcours_id == Parcours.id)
            .outerjoin(
                Specialisation,
                FormationElement.specialisation_id == Specialisation.id,
            )
            .where(
                FormationElement.actif.is_(True),
                or_(
                    FormationElement.formation_id.is_(None),
                    and_(Formation.actif.is_(True), Parcours.actif.is_(True)),
                ),
                or_(
                    FormationElement.specialisation_id.is_(None),
                    Specialisation.actif.is_(True),
                ),
            )
        )

    async def dependency_counts(self, entity_id: int) -> dict[str, int]:
        count = int(
            (
                await self.session.scalar(
                    select(func.count(FormationElement.id)).where(
                        FormationElement.parent_id == entity_id
                    )
                )
            )
            or 0
        )
        return {"child_elements": count} if count else {}

