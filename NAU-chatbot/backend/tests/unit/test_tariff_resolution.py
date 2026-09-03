from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.sqlalchemy import Tarif
from app.services.academic.tariff_resolution import TarifScope, resolve_tariff_precedence


pytestmark = pytest.mark.unit


def _tarif(
    tarif_id: int,
    *,
    parcours_id: int | None = None,
    formation_id: int | None = None,
    specialisation_id: int | None = None,
    langue: str | None = None,
    frais: str | None = None,
    mensualite: str | None = None,
) -> Tarif:
    return Tarif(
        id=tarif_id,
        parcours_id=parcours_id,
        formation_id=formation_id,
        specialisation_id=specialisation_id,
        langue_enseignement=langue,
        frais_inscription=Decimal(frais) if frais else None,
        mensualite=Decimal(mensualite) if mensualite else None,
        devise="TND",
        statut="INDICATIF",
        actif=True,
    )


def test_cycle_fee_and_formation_tuition_are_composed() -> None:
    result = resolve_tariff_precedence(
        [
            _tarif(1, parcours_id=2, frais="800"),
            _tarif(2, formation_id=20, langue="FRANCAIS", mensualite="900"),
        ],
        parcours_id=2,
        formation_id=20,
        langue_enseignement="FRANCAIS",
    )

    assert result.frais_inscription == Decimal("800")
    assert result.mensualite == Decimal("900")
    assert result.field_origins["frais_inscription"] is TarifScope.PARCOURS
    assert result.field_origins["mensualite"] is TarifScope.FORMATION


def test_french_and_english_tariffs_remain_distinct() -> None:
    common = _tarif(1, parcours_id=2, frais="800")
    french = _tarif(2, formation_id=20, langue="FRANCAIS", mensualite="900")
    english = _tarif(3, formation_id=20, langue="ANGLAIS", mensualite="1200")

    result_fr = resolve_tariff_precedence(
        [common, french],
        parcours_id=2,
        formation_id=20,
        langue_enseignement="FRANCAIS",
    )
    result_en = resolve_tariff_precedence(
        [common, english],
        parcours_id=2,
        formation_id=20,
        langue_enseignement="ANGLAIS",
    )

    assert result_fr.mensualite == Decimal("900")
    assert result_en.mensualite == Decimal("1200")
    assert result_fr.frais_inscription == result_en.frais_inscription == Decimal("800")
