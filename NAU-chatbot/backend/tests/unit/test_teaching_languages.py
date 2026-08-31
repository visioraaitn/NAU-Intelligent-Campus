from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.schemas.academic import FormationCreate, TarifCreate


pytestmark = pytest.mark.unit


def test_formation_languages_are_required_normalized_and_unique() -> None:
    formation = FormationCreate(
        parcours_id=1,
        code="LICENCE_TEST",
        nom="Licence test",
        langues_enseignement=[" francais ", "anglais", "FRANCAIS"],
    )

    assert formation.langues_enseignement == ["FRANCAIS", "ANGLAIS"]


@pytest.mark.parametrize("languages", [None, []])
def test_formation_rejects_missing_or_empty_languages(languages: object) -> None:
    payload = {
        "parcours_id": 1,
        "code": "LICENCE_TEST",
        "nom": "Licence test",
    }
    if languages is not None:
        payload["langues_enseignement"] = languages

    with pytest.raises(ValidationError):
        FormationCreate.model_validate(payload)


def test_tariff_language_is_required_and_normalized() -> None:
    tariff = TarifCreate(
        formation_id=1,
        langue_enseignement=" anglais ",
        frais_inscription=Decimal("800.00"),
    )

    assert tariff.langue_enseignement == "ANGLAIS"


def test_tariff_rejects_an_invalid_language_code() -> None:
    with pytest.raises(ValidationError):
        TarifCreate(
            formation_id=1,
            langue_enseignement="français libre",
        )
