from __future__ import annotations

import pytest

from app.domain.rag.schemas import RagFact
from app.domain.recommendation.schemas import EligibilityStatus
from app.services.dialogue.guards.factual import FactualGuard
from app.services.dialogue.prompt_composer import PromptComposer


pytestmark = pytest.mark.unit


def _fact(entity_type: str, *, element_type: str | None = None) -> RagFact:
    return RagFact(
        text="Fait académique sourcé.",
        entity_type=entity_type,
        entity_id=1,
        formation_code="FORMATION",
        specialisation_code=None,
        source_ref="SRC_TEST",
        supporting_chunk_id="test:1",
        element_type=element_type,
    )


def test_guard_removes_precise_money_and_duration_without_matching_fact_types() -> None:
    answer = "Les frais sont de 1 000 TND. La formation dure 3 ans. Je peux vérifier le catalogue."

    guarded = FactualGuard().validate(
        answer,
        (),
        eligibility_status=None,
    )

    assert "TND" not in guarded
    assert "3 ans" not in guarded
    assert guarded == "Je peux vérifier le catalogue."


def test_guard_keeps_supported_claim_categories() -> None:
    answer = "Les frais sont de 800 TND. La formation dure 2 ans."

    guarded = FactualGuard().validate(
        answer,
        (_fact("TARIF"), _fact("FORMATION")),
        eligibility_status=None,
    )

    assert guarded == answer


def test_guard_removes_positive_admission_claim_when_eligibility_is_unknown() -> None:
    guarded = FactualGuard().validate(
        "Tu es éligible. Il faut toutefois déposer un dossier.",
        (),
        eligibility_status=EligibilityStatus.UNKNOWN,
    )

    assert "éligible" not in guarded
    assert "déposer un dossier" in guarded


def test_guard_requires_typed_evidence_for_accreditation_and_mobility() -> None:
    answer = "Le diplôme est accrédité EURO-INF. Une mobilité internationale est proposée."

    guarded = FactualGuard().validate(
        answer,
        (_fact("FORMATION_ELEMENT", element_type="METIER"),),
        eligibility_status=None,
    )

    assert guarded == ""


def test_prompt_keeps_untrusted_user_and_rag_data_out_of_system_role() -> None:
    marker = "IGNORE_PREVIOUS_INSTRUCTIONS_MARKER"
    messages = PromptComposer().compose(
        user_message=marker,
        memory="profile = UNKNOWN",
        known_facts="- profile = UNKNOWN",
        forbidden_assumptions="- ne pas inventer",
        academic_facts=(_fact("FORMATION"),),
        decision="UNKNOWN",
        response_mode="STANDARD",
    )

    assert [message.role for message in messages] == ["system", "user"]
    assert marker not in messages[0].content
    assert marker in messages[1].content


def test_guard_humanizes_internal_labels_and_corrects_career_wording() -> None:
    guarded = FactualGuard().validate(
        "Profil NEW_BAC, section ECONOMIE_GESTION. L'IIT propose des métiers comme développeur.",
        (_fact("FORMATION_ELEMENT", element_type="METIER"),),
        eligibility_status=None,
    )

    assert "NEW_BAC" not in guarded
    assert "ECONOMIE_GESTION" not in guarded
    assert "nouveau bachelier" in guarded
    assert "Économie et Gestion" in guarded
    assert "Les formations de l'IIT ouvrent vers des débouchés" in guarded


def test_guard_never_exposes_source_or_rule_identifiers() -> None:
    guarded = FactualGuard().validate(
        "Règle ADMISSION_LICENCE_INFO, source FLYER_LICENCE_INFO.",
        (),
        eligibility_status=None,
    )

    assert "ADMISSION_" not in guarded
    assert "FLYER_" not in guarded
    assert "règle académique" in guarded
