from __future__ import annotations

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import aliased

from app.models.sqlalchemy import Formation, Parcours, Specialisation, Tarif
from app.repositories.academic.base import AcademicRepository


class TarifRepository(AcademicRepository[Tarif]):
    model = Tarif
    resource_name = "tarif"
    writable_fields = frozenset(
        {
            "parcours_id",
            "formation_id",
            "specialisation_id",
            "frais_inscription",
            "mensualite",
            "nb_mensualites",
            "langue_enseignement",
            "devise",
            "annee_universitaire",
            "statut",
            "remarque",
            "source_ref",
            "actif",
        }
    )
    filter_fields = {
        "parcours_id": Tarif.parcours_id,
        "formation_id": Tarif.formation_id,
        "specialisation_id": Tarif.specialisation_id,
        "annee_universitaire": Tarif.annee_universitaire,
        "langue_enseignement": Tarif.langue_enseignement,
        "statut": Tarif.statut,
        "devise": Tarif.devise,
        "actif": Tarif.actif,
    }
    search_fields = (
        Tarif.annee_universitaire,
        Tarif.langue_enseignement,
        Tarif.statut,
        Tarif.remarque,
        Tarif.source_ref,
    )
    order_by = (
        Tarif.annee_universitaire.desc().nullslast(),
        Tarif.langue_enseignement.asc().nullsfirst(),
        Tarif.id.desc(),
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
        direct_parcours = aliased(Parcours)
        return (
            statement.outerjoin(Formation, Tarif.formation_id == Formation.id)
            .outerjoin(
                formation_parcours,
                Formation.parcours_id == formation_parcours.id,
            )
            .outerjoin(direct_parcours, Tarif.parcours_id == direct_parcours.id)
            .outerjoin(Specialisation, Tarif.specialisation_id == Specialisation.id)
            .where(
                Tarif.actif.is_(True),
                or_(Tarif.parcours_id.is_(None), direct_parcours.actif.is_(True)),
                or_(
                    Tarif.formation_id.is_(None),
                    and_(
                        Formation.actif.is_(True),
                        formation_parcours.actif.is_(True),
                    ),
                ),
                or_(
                    Tarif.specialisation_id.is_(None),
                    Specialisation.actif.is_(True),
                ),
            )
        )

    async def list_applicable(
        self,
        *,
        parcours_id: int,
        formation_id: int,
        specialisation_id: int | None = None,
        langue_enseignement: str | None = None,
        include_inactive: bool = False,
    ) -> list[Tarif]:
        scopes = [
            and_(Tarif.parcours_id == parcours_id, Tarif.formation_id.is_(None)),
            and_(
                Tarif.parcours_id.is_(None),
                Tarif.formation_id == formation_id,
                Tarif.specialisation_id.is_(None),
            ),
        ]
        if specialisation_id is not None:
            scopes.append(
                and_(
                    Tarif.parcours_id.is_(None),
                    Tarif.formation_id == formation_id,
                    Tarif.specialisation_id == specialisation_id,
                )
            )
        statement = select(Tarif).where(
            or_(*scopes),
            or_(
                Tarif.langue_enseignement.is_(None),
                Tarif.langue_enseignement == langue_enseignement,
            ),
        )
        statement = self._apply_scope(statement, include_inactive=include_inactive)
        result = await self.session.scalars(statement.order_by(Tarif.id.asc()))
        return list(result.unique().all())
