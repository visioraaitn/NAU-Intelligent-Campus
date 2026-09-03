from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import cast

from app.models.sqlalchemy import Tarif
from app.repositories.academic import TarifRepository


class TarifScope(StrEnum):
    PARCOURS = "PARCOURS"
    FORMATION = "FORMATION"
    SPECIALISATION = "SPECIALISATION"


@dataclass(frozen=True, slots=True)
class EffectiveTarif:
    parcours_id: int
    formation_id: int
    specialisation_id: int | None
    langue_enseignement: str | None
    frais_inscription: Decimal | None
    mensualite: Decimal | None
    nb_mensualites: int | None
    devise: str
    annee_universitaire: str | None
    statut: str
    remarque: str | None
    source_ref: str | None
    field_origins: dict[str, TarifScope]
    source_tarif_ids: tuple[int, ...]


class AcademicTariffResolutionService:
    """Compose non-null tariff components from broad to specific scope."""

    def __init__(self, repository: TarifRepository) -> None:
        self.repository = repository

    async def resolve_effective_tarif(
        self,
        *,
        parcours_id: int,
        formation_id: int,
        specialisation_id: int | None = None,
        langue_enseignement: str | None = None,
        include_inactive: bool = False,
    ) -> EffectiveTarif:
        tarifs = await self.repository.list_applicable(
            parcours_id=parcours_id,
            formation_id=formation_id,
            specialisation_id=specialisation_id,
            langue_enseignement=langue_enseignement,
            include_inactive=include_inactive,
        )
        return resolve_tariff_precedence(
            tarifs,
            parcours_id=parcours_id,
            formation_id=formation_id,
            specialisation_id=specialisation_id,
            langue_enseignement=langue_enseignement,
        )


def resolve_tariff_precedence(
    tarifs: list[Tarif],
    *,
    parcours_id: int,
    formation_id: int,
    specialisation_id: int | None = None,
    langue_enseignement: str | None = None,
) -> EffectiveTarif:
    values: dict[str, object | None] = {
        "frais_inscription": None,
        "mensualite": None,
        "nb_mensualites": None,
        "devise": "TND",
        "annee_universitaire": None,
        "statut": "INDICATIF",
        "remarque": None,
        "source_ref": None,
    }
    origins: dict[str, TarifScope] = {}
    ordered = sorted(
        tarifs,
        key=lambda item: (
            _SCOPE_PRIORITY[_scope(item)],
            item.langue_enseignement is not None,
            item.id,
        ),
    )
    for tarif in ordered:
        scope = _scope(tarif)
        for field in values:
            value = getattr(tarif, field)
            if value is not None:
                values[field] = value
                origins[field] = scope

    return EffectiveTarif(
        parcours_id=parcours_id,
        formation_id=formation_id,
        specialisation_id=specialisation_id,
        langue_enseignement=langue_enseignement,
        frais_inscription=cast(Decimal | None, values["frais_inscription"]),
        mensualite=cast(Decimal | None, values["mensualite"]),
        nb_mensualites=cast(int | None, values["nb_mensualites"]),
        devise=str(values["devise"]),
        annee_universitaire=cast(str | None, values["annee_universitaire"]),
        statut=str(values["statut"]),
        remarque=cast(str | None, values["remarque"]),
        source_ref=cast(str | None, values["source_ref"]),
        field_origins=origins,
        source_tarif_ids=tuple(item.id for item in ordered),
    )


def _scope(tarif: Tarif) -> TarifScope:
    if tarif.specialisation_id is not None:
        return TarifScope.SPECIALISATION
    if tarif.formation_id is not None:
        return TarifScope.FORMATION
    return TarifScope.PARCOURS


_SCOPE_PRIORITY = {
    TarifScope.PARCOURS: 0,
    TarifScope.FORMATION: 1,
    TarifScope.SPECIALISATION: 2,
}
