from __future__ import annotations

from sqlalchemy import Select, or_

from app.models.sqlalchemy import Formation, Parcours, Specialisation, Tarif
from app.repositories.academic.base import AcademicRepository


class TarifRepository(AcademicRepository[Tarif]):
    model = Tarif
    resource_name = "tarif"
    writable_fields = frozenset(
        {
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
        Tarif.langue_enseignement.asc(),
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
        return (
            statement.join(Formation, Tarif.formation_id == Formation.id)
            .join(Parcours, Formation.parcours_id == Parcours.id)
            .outerjoin(Specialisation, Tarif.specialisation_id == Specialisation.id)
            .where(
                Tarif.actif.is_(True),
                Formation.actif.is_(True),
                Parcours.actif.is_(True),
                or_(Tarif.specialisation_id.is_(None), Specialisation.actif.is_(True)),
            )
        )
