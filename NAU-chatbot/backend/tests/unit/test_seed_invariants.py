from __future__ import annotations

from pathlib import Path

import pytest
import yaml


pytestmark = pytest.mark.unit


SEED_PATH = Path(__file__).resolve().parents[2] / "app" / "data" / "academic_seed.yaml"


@pytest.fixture(scope="module")
def seed() -> dict[str, object]:
    return yaml.safe_load(SEED_PATH.read_text(encoding="utf-8"))


def test_seed_contains_exactly_the_seven_academic_business_collections(seed) -> None:
    business_collections = {
        key
        for key, value in seed.items()
        if key not in {"version", "dataset"} and isinstance(value, list)
    }

    assert business_collections == {
        "parcours",
        "formations",
        "specialisations",
        "formation_elements",
        "tarifs",
        "orientation_rules",
        "accreditations",
    }


def test_seed_has_active_mp_and_the_corrected_prepa_rule(seed) -> None:
    mp = next(
        item
        for item in seed["specialisations"]
        if item["formation_code"] == "PREPA_GENERAL" and item["code"] == "MP"
    )
    rule = next(
        item for item in seed["orientation_rules"] if item["code"] == "ADMISSION_PREPA"
    )

    assert mp["actif"] is True
    assert mp["source_ref"] == "PROJECT_INSTITUTIONAL_RULES"
    assert rule["actif"] is True
    assert rule["source_ref"] == "PROJECT_INSTITUTIONAL_RULES"
    assert set(rule["criteres"]["type_bac"]["in"]) == {"MATH", "SCIENCES"}


def test_seed_does_not_invent_a_prepa_accreditation(seed) -> None:
    assert all(
        item["formation_code"] != "PREPA_GENERAL"
        for item in seed["accreditations"]
    )
    assert {
        (item["formation_code"], item["code"], item["organisme"])
        for item in seed["accreditations"]
        if item["actif"]
    } == {("INGENIEUR_INFO", "EURO-INF", "ASIIN")}


def test_seed_assigns_the_requested_teaching_languages(seed) -> None:
    formations = {item["code"]: item for item in seed["formations"]}
    bilingual = {
        "LICENCE_INFO",
        "LICENCE_ELEC_SEIER",
        "LICENCE_MECATRONIQUE_SI",
    }

    for code, formation in formations.items():
        expected = {"FRANCAIS", "ANGLAIS"} if code in bilingual else {"FRANCAIS"}
        assert set(formation["langues_enseignement"]) == expected

    for tarif in seed["tarifs"]:
        assert tarif["langue_enseignement"] in formations[tarif["formation_code"]][
            "langues_enseignement"
        ]
