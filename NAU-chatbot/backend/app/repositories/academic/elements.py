from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import aliased

from app.domain.academic.enums import FormationElementType
from app.models.sqlalchemy import Formation, FormationElement, Parcours, Specialisation
from app.repositories.academic.base import AcademicRepository


class FormationElementRepository(AcademicRepository[FormationElement]):
    model = FormationElement
    resource_name = "element de formation"
    writable_fields = frozenset(
        {
            "parcours_id",
            "formation_id",
            "specialisation_id",
            "parent_id",
            "type_element",
            "code",
            "nom",
            "description",
            "valeur",
            "organisme",
            "ordre_affichage",
            "source_ref",
            "actif",
        }
    )
    filter_fields = {
        "parcours_id": FormationElement.parcours_id,
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
        FormationElement.valeur,
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
        formation_parcours = aliased(Parcours)
        element_parcours = aliased(Parcours)
        return (
            statement.outerjoin(Formation, FormationElement.formation_id == Formation.id)
            .outerjoin(formation_parcours, Formation.parcours_id == formation_parcours.id)
            .outerjoin(element_parcours, FormationElement.parcours_id == element_parcours.id)
            .outerjoin(
                Specialisation,
                FormationElement.specialisation_id == Specialisation.id,
            )
            .where(
                FormationElement.actif.is_(True),
                or_(
                    FormationElement.parcours_id.is_(None),
                    element_parcours.actif.is_(True),
                ),
                or_(
                    FormationElement.formation_id.is_(None),
                    and_(Formation.actif.is_(True), formation_parcours.actif.is_(True)),
                ),
                or_(
                    FormationElement.specialisation_id.is_(None),
                    Specialisation.actif.is_(True),
                ),
            )
        )

    async def list_applicable(
        self,
        *,
        parcours_id: int,
        formation_id: int | None = None,
        specialisation_id: int | None = None,
        element_types: Sequence[FormationElementType] | None = None,
        include_inactive: bool = False,
    ) -> list[FormationElement]:
        scopes = [
            and_(
                FormationElement.parcours_id.is_(None),
                FormationElement.formation_id.is_(None),
                FormationElement.specialisation_id.is_(None),
            ),
            and_(
                FormationElement.parcours_id == parcours_id,
                FormationElement.formation_id.is_(None),
                FormationElement.specialisation_id.is_(None),
            ),
        ]
        if formation_id is not None:
            scopes.append(
                and_(
                    FormationElement.parcours_id.is_(None),
                    FormationElement.formation_id == formation_id,
                    FormationElement.specialisation_id.is_(None),
                )
            )
        if formation_id is not None and specialisation_id is not None:
            scopes.append(
                and_(
                    FormationElement.parcours_id.is_(None),
                    FormationElement.formation_id == formation_id,
                    FormationElement.specialisation_id == specialisation_id,
                )
            )

        statement: Select[tuple[FormationElement]] = select(FormationElement).where(or_(*scopes))
        statement = self._apply_scope(statement, include_inactive=include_inactive)
        if element_types:
            statement = statement.where(FormationElement.type_element.in_(element_types))
        statement = statement.order_by(*self.order_by)
        result = await self.session.scalars(statement)
        return list(result.unique().all())

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
