from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.conversation.models import (
    AcademicProfile,
    ConversationState,
    ConversationSubject,
    SubjectState,
)
from app.domain.recommendation.schemas import (
    EligibilityDecision,
    EligibilityStatus,
    RecommendationDecision,
    RecommendationOption,
)
from app.services.dialogue.conversion_cta import ConversionCTA
from app.services.dialogue.dialogue_act_detector import DialogueAct
from app.services.dialogue.guards.anti_repetition import AntiRepetitionGuard
from app.services.recommendation.recommendation_service import RecommendationService


pytestmark = pytest.mark.unit


class AlwaysEligible:
    async def evaluate(self, subject, formation, specialisation=None):
        del subject
        return EligibilityDecision(
            EligibilityStatus.ELIGIBLE,
            formation.id,
            formation.code,
            specialisation.id if specialisation else None,
            specialisation.code if specialisation else None,
        )


def _catalogue(repository_factory):
    parcours = [SimpleNamespace(id=1, code="INGENIEUR", actif=True)]
    formations = [
        SimpleNamespace(
            id=10,
            parcours_id=1,
            code="INGENIEUR_INFO",
            nom="Génie Informatique",
            description="Formation ingénieur informatique",
            actif=True,
        )
    ]
    specialisations = [
        SimpleNamespace(
            id=101,
            formation_id=10,
            code="SDIA",
            nom="Science des Données et Intelligence Artificielle",
            description="Data, IA, analyse et machine learning",
            actif=True,
        ),
        SimpleNamespace(
            id=102,
            formation_id=10,
            code="ARSI",
            nom="Administration Réseau et Sécurité Informatique",
            description="Réseaux, systèmes, cybersécurité et DevSecOps",
            actif=True,
        ),
        SimpleNamespace(
            id=103,
            formation_id=10,
            code="GLID",
            nom="Génie Logiciel et Informatique Décisionnelle",
            description="Logiciel, web, cloud et informatique décisionnelle",
            actif=True,
        ),
    ]
    elements = [
        SimpleNamespace(
            id=201,
            formation_id=10,
            specialisation_id=101,
            nom="Machine Learning",
            description="Big data et intelligence artificielle",
            actif=True,
        ),
        SimpleNamespace(
            id=202,
            formation_id=10,
            specialisation_id=102,
            nom="Cybersécurité",
            description="Sécurité réseau",
            actif=True,
        ),
        SimpleNamespace(
            id=203,
            formation_id=10,
            specialisation_id=103,
            nom="Développement logiciel",
            description="Web et cloud",
            actif=True,
        ),
    ]
    return SimpleNamespace(
        parcours=repository_factory(parcours),
        formations=repository_factory(formations),
        specialisations=repository_factory(specialisations),
        elements=repository_factory(elements),
    )


def _new_bac_catalogue(repository_factory):
    parcours = [
        SimpleNamespace(id=1, code="PREPA", actif=True),
        SimpleNamespace(id=2, code="LICENCE", actif=True),
        SimpleNamespace(id=3, code="INGENIEUR", actif=True),
        SimpleNamespace(id=4, code="ARCHITECTURE", actif=True),
    ]
    formations = [
        SimpleNamespace(
            id=10,
            parcours_id=1,
            code="PREPA_GENERAL",
            nom="Cycle Préparatoire",
            description="Préparation aux études d'ingénieur",
            intitule_diplome=None,
            duree_annees=2,
            actif=True,
        ),
        SimpleNamespace(
            id=20,
            parcours_id=2,
            code="LICENCE_INFO",
            nom="Licence en Informatique",
            description="Informatique",
            intitule_diplome="Licence en Informatique",
            duree_annees=3,
            actif=True,
        ),
        SimpleNamespace(
            id=25,
            parcours_id=2,
            code="LICENCE_MECATRONIQUE_SI",
            nom="Mécatronique & Systèmes Intelligents",
            description="Mécatronique, IoT et systèmes intelligents",
            intitule_diplome="Licence Nationale en Mécatronique & Systèmes Intelligents",
            duree_annees=3,
            actif=True,
        ),
        SimpleNamespace(
            id=30,
            parcours_id=3,
            code="INGENIEUR_INFO",
            nom="Génie Informatique",
            description="Cycle ingénieur",
            intitule_diplome=None,
            duree_annees=3,
            actif=True,
        ),
        SimpleNamespace(
            id=40,
            parcours_id=4,
            code="ARCHITECTURE_DNA",
            nom="Diplôme National d'Architecte",
            description="Architecture",
            intitule_diplome="Diplôme National d'Architecte",
            duree_annees=6,
            actif=True,
        ),
    ]
    return SimpleNamespace(
        parcours=repository_factory(parcours),
        formations=repository_factory(formations),
        specialisations=repository_factory(),
        elements=repository_factory(),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("bac", ["MATH", "SCIENCES"])
async def test_new_scientific_bac_prioritizes_prepa_and_keeps_licence_options(
    bac: str,
    repository_factory,
) -> None:
    service = RecommendationService(
        _new_bac_catalogue(repository_factory),
        AlwaysEligible(),
    )

    decision = await service.recommend(
        SubjectState(profile=AcademicProfile.NEW_BAC, bac_specialty=bac)
    )

    assert decision.primary is not None
    assert decision.primary.formation_code == "PREPA_GENERAL"
    assert decision.secondary is not None
    assert decision.secondary.formation_code == "LICENCE_INFO"
    assert {option.formation_code for option in decision.alternatives} == {
        "LICENCE_INFO",
        "LICENCE_MECATRONIQUE_SI",
    }


@pytest.mark.asyncio
async def test_new_economics_bac_is_routed_only_to_licence(
    repository_factory,
) -> None:
    service = RecommendationService(
        _new_bac_catalogue(repository_factory),
        AlwaysEligible(),
    )

    decision = await service.recommend(
        SubjectState(
            profile=AcademicProfile.NEW_BAC,
            bac_specialty="ECONOMIE_GESTION",
        )
    )

    assert decision.primary is not None
    assert decision.primary.formation_code == "LICENCE_INFO"
    assert decision.secondary is None
    assert decision.alternatives == ()
    assert "Ingénieur" not in decision.primary.formation_name


@pytest.mark.asyncio
async def test_recommendation_ranks_data_ai_and_excludes_rejected_offer(
    repository_factory,
) -> None:
    service = RecommendationService(_catalogue(repository_factory), AlwaysEligible())
    subject = SubjectState(
        profile=AcademicProfile.LICENCE_HOLDER,
        licence_specialty="INFORMATIQUE",
        interests=["DATA_AI"],
        target="ENGINEERING",
    )

    first = await service.recommend(subject)
    assert first.primary is not None
    assert first.primary.specialisation_code == "SDIA"
    assert first.primary.eligibility.status is EligibilityStatus.ELIGIBLE

    subject.rejected_offers.append("SDIA")
    alternative = await service.recommend(subject)

    assert alternative.primary is not None
    assert alternative.primary.specialisation_code != "SDIA"
    assert all(
        option is None or option.specialisation_code != "SDIA"
        for option in (alternative.primary, alternative.secondary)
    )


@pytest.mark.asyncio
async def test_rejected_informatics_domain_suppresses_informatics_recommendation(
    repository_factory,
) -> None:
    service = RecommendationService(_catalogue(repository_factory), AlwaysEligible())
    subject = SubjectState(
        profile=AcademicProfile.LICENCE_HOLDER,
        interests=["DATA_AI"],
        rejected_domains=["INFORMATIQUE"],
    )

    decision = await service.recommend(subject)

    assert decision.primary is None
    assert decision.secondary is None


def _recommendation(
    status: EligibilityStatus = EligibilityStatus.ELIGIBLE,
) -> RecommendationDecision:
    eligibility = EligibilityDecision(
        status,
        10,
        "INGENIEUR_INFO",
        101,
        "SDIA",
    )
    primary = RecommendationOption(
        10,
        "INGENIEUR_INFO",
        "Génie Informatique",
        101,
        "SDIA",
        "Science des Données et Intelligence Artificielle",
        5.0,
        eligibility,
    )
    return RecommendationDecision(primary, None)


def test_conversion_cta_is_eligible_scoped_capped_and_cooled_down() -> None:
    conversation = ConversationState.new(uuid4())
    conversation.turn_count = 4
    subject = conversation.active_state
    recommendation = _recommendation()
    policy = ConversionCTA()

    assert not policy.should_add(
        conversation,
        subject,
        ["ORIENTATION"],
        DialogueAct.EXPRESS_INTEREST,
        _recommendation(EligibilityStatus.NOT_ELIGIBLE),
    )
    assert policy.should_add(
        conversation,
        subject,
        ["ORIENTATION"],
        DialogueAct.ASK_INFORMATION,
        recommendation,
    )
    answer = policy.add("La piste SDIA correspond à ton intérêt Data/IA.", subject, 4)

    assert "pré-inscription" in answer
    assert "sans te promettre l'admission" in answer
    assert subject.cta_count == 1
    assert not policy.should_add(
        conversation,
        subject,
        ["ORIENTATION"],
        DialogueAct.ASK_INFORMATION,
        recommendation,
    )

    conversation.turn_count = 7
    assert not policy.should_add(
        conversation,
        subject,
        ["FEES"],
        DialogueAct.ASK_INFORMATION,
        recommendation,
    )

    subject.cta_count = 2
    conversation.turn_count = 10
    assert not policy.should_add(
        conversation,
        subject,
        ["ORIENTATION"],
        DialogueAct.EXPRESS_INTEREST,
        recommendation,
    )

    conversation.active_subject = ConversationSubject.HYPOTHETICAL
    assert not policy.should_add(
        conversation,
        conversation.active_state,
        ["ORIENTATION"],
        DialogueAct.EXPRESS_INTEREST,
        recommendation,
    )


def test_anti_repetition_drops_a_repeated_leading_line() -> None:
    previous = (
        "SDIA couvre la data, l'intelligence artificielle et le machine learning.\n"
        "Cette piste correspond à un intérêt marqué pour l'analyse de données."
    )
    repeated = previous

    guarded = AntiRepetitionGuard().apply(repeated, previous)

    assert guarded == "Cette piste correspond à un intérêt marqué pour l'analyse de données."
    assert guarded != repeated
