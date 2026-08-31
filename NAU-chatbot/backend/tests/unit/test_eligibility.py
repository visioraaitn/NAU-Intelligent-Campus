from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.domain.conversation.models import AcademicProfile, SubjectState
from app.domain.recommendation.schemas import EligibilityStatus
from app.services.eligibility.eligibility_service import EligibilityService


pytestmark = pytest.mark.unit


def _formation(
    entity_id: int,
    code: str,
    name: str,
    *,
    parcours_id: int = 1,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=entity_id,
        code=code,
        nom=name,
        parcours_id=parcours_id,
        actif=True,
    )


def _specialisation(
    entity_id: int,
    formation_id: int,
    code: str,
    name: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=entity_id,
        formation_id=formation_id,
        code=code,
        nom=name,
        actif=True,
    )


def _admission_rule(
    entity_id: int,
    formation_id: int,
    code: str,
    criteria: dict[str, object],
    *,
    specialisation_id: int | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=entity_id,
        formation_id=formation_id,
        specialisation_id=specialisation_id,
        code=code,
        type_regle="ADMISSION",
        criteres=criteria,
        description=f"Admission contrôlée par {code}",
        source_ref="PROJECT_INSTITUTIONAL_RULES",
        actif=True,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("bac", ["MATH", "SCIENCES"])
async def test_prepa_mp_accepts_only_the_two_authorized_scientific_bacs(
    bac: str,
    repository_factory,
) -> None:
    prepa = _formation(10, "PREPA_GENERAL", "Cycle Préparatoire")
    mp = _specialisation(101, prepa.id, "MP", "Mathématiques-Physique")
    rule = _admission_rule(
        1,
        prepa.id,
        "ADMISSION_PREPA",
        {"diplome": "BAC", "type_bac": {"in": ["MATH", "SCIENCES"]}},
    )
    subject = SubjectState(profile=AcademicProfile.NEW_BAC, bac_specialty=bac)

    decision = await EligibilityService(repository_factory([rule])).evaluate(
        subject,
        prepa,
        mp,
    )

    assert decision.status is EligibilityStatus.ELIGIBLE
    assert decision.formation_code == "PREPA_GENERAL"
    assert decision.specialisation_code == "MP"
    assert decision.source_refs == ("PROJECT_INSTITUTIONAL_RULES",)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bac",
    ["INFORMATIQUE", "TECHNIQUE", "ECONOMIE_GESTION", "SPORT"],
)
async def test_prepa_rejects_info_technique_economics_and_sport_bacs(
    bac: str,
    repository_factory,
) -> None:
    prepa = _formation(10, "PREPA_GENERAL", "Cycle Préparatoire")
    mp = _specialisation(101, prepa.id, "MP", "Mathématiques-Physique")
    rule = _admission_rule(
        1,
        prepa.id,
        "ADMISSION_PREPA",
        {"diplome": "BAC", "type_bac": {"in": ["MATH", "SCIENCES"]}},
    )
    subject = SubjectState(profile=AcademicProfile.NEW_BAC, bac_specialty=bac)

    decision = await EligibilityService(repository_factory([rule])).evaluate(
        subject,
        prepa,
        mp,
    )

    assert decision.status is EligibilityStatus.NOT_ELIGIBLE
    assert decision.matched_rules == ()
    assert decision.failed_rules[0].rule_code == "ADMISSION_PREPA"
    assert bac in decision.failed_rules[0].reason


@pytest.mark.asyncio
async def test_prepa_eligibility_stays_unknown_until_bac_section_is_known(
    repository_factory,
) -> None:
    prepa = _formation(10, "PREPA_GENERAL", "Cycle Préparatoire")
    rule = _admission_rule(
        1,
        prepa.id,
        "ADMISSION_PREPA",
        {"diplome": "BAC", "type_bac": {"in": ["MATH", "SCIENCES"]}},
    )

    decision = await EligibilityService(repository_factory([rule])).evaluate(
        SubjectState(profile=AcademicProfile.NEW_BAC),
        prepa,
    )

    assert decision.status is EligibilityStatus.UNKNOWN
    assert decision.unknown_reasons == ("La section du bac est inconnue.",)


@pytest.mark.asyncio
async def test_engineering_accepts_a_completed_prepa_but_not_an_unfinished_one(
    repository_factory,
) -> None:
    engineering = _formation(20, "INGENIEUR_INFO", "Génie Informatique")
    rule = _admission_rule(
        2,
        engineering.id,
        "ADMISSION_INGENIEUR_INFO",
        {"diplome": {"in": ["PREPA", "LICENCE", "MASTER"]}},
    )
    service = EligibilityService(repository_factory([rule]))

    completed = await service.evaluate(
        SubjectState(profile=AcademicProfile.PREPA_HOLDER),
        engineering,
    )
    still_studying = await service.evaluate(
        SubjectState(
            profile=AcademicProfile.PREPA_STUDENT,
            finishing_current_degree=False,
        ),
        engineering,
    )
    finishing = await service.evaluate(
        SubjectState(
            profile=AcademicProfile.PREPA_STUDENT,
            finishing_current_degree=True,
        ),
        engineering,
    )

    assert completed.status is EligibilityStatus.ELIGIBLE
    assert still_studying.status is EligibilityStatus.UNKNOWN
    assert "terminé ou validé" in still_studying.unknown_reasons[0]
    assert finishing.status is EligibilityStatus.ELIGIBLE

