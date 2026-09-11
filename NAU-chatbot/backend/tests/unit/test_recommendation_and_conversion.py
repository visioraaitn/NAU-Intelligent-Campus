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
from app.services.dialogue.structured_response import StructuredResponseBuilder
from app.services.recommendation.recommendation_service import RecommendationService


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("specialty", "formation_code", "expected"),
    [
        ("INFO_DE_GESTION", "INGENIEUR_INFO", True),
        ("IDUS", "INGENIEUR_INDUSTRIEL", True),
        ("DROIT", "INGENIEUR_INFO", True),
    ],
)
def test_external_or_misspelled_licence_still_allows_engineering_path(
    specialty: str,
    formation_code: str,
    expected: bool,
) -> None:
    subject = SubjectState(
        profile=AcademicProfile.LICENCE_HOLDER,
        licence_specialty=specialty,
    )

    assert RecommendationService._formation_matches_academic_domain(
        subject,
        formation_code,
    ) is expected


@pytest.mark.parametrize(
    ("specialty", "formation_code", "expected"),
    [
        ("INFO_DE_GESTION", "INGENIEUR_INFO", True),
        ("COMPTABILITE", "INGENIEUR_INFO", True),
        ("ELECTROMECANIQUE", "INGENIEUR_INDUSTRIEL", True),
        ("ENERGETIQUE", "INGENIEUR_PROCEDES", True),
    ],
)
def test_tunisian_licence_sections_map_to_engineering_domains(
    specialty: str,
    formation_code: str,
    expected: bool,
) -> None:
    assert RecommendationService._formation_matches_academic_domain(
        SubjectState(
            profile=AcademicProfile.LICENCE_HOLDER,
            licence_specialty=specialty,
        ),
        formation_code,
    ) is expected


def test_licence_student_who_wants_to_continue_at_iit_keeps_licence_path() -> None:
    subject = SubjectState(
        profile=AcademicProfile.LICENCE_STUDENT,
        target="LICENCE",
        licence_specialty="INFO_DE_GESTION",
    )

    assert RecommendationService._allowed_parcours(subject) == {"LICENCE"}
    assert RecommendationService._formation_matches_academic_domain(
        subject,
        "LICENCE_INFO",
    )


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
            intitule_diplome="Diplôme National d'Ingénieur en Génie Informatique",
            duree_annees=3,
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
            type_element=SimpleNamespace(value="MODULE"),
            nom="Machine Learning",
            description="Big data et intelligence artificielle",
            actif=True,
        ),
        SimpleNamespace(
            id=202,
            formation_id=10,
            specialisation_id=102,
            type_element=SimpleNamespace(value="MODULE"),
            nom="Cybersécurité",
            description="Sécurité réseau",
            actif=True,
        ),
        SimpleNamespace(
            id=203,
            formation_id=10,
            specialisation_id=103,
            type_element=SimpleNamespace(value="MODULE"),
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
async def test_new_scientific_bac_prioritizes_licences_and_keeps_prepa_last(
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
    assert decision.primary.formation_code == "LICENCE_INFO"
    assert decision.secondary is not None
    assert decision.secondary.formation_code == "LICENCE_MECATRONIQUE_SI"
    assert tuple(option.formation_code for option in decision.alternatives) == (
        "LICENCE_MECATRONIQUE_SI",
        "PREPA_GENERAL",
    )


@pytest.mark.asyncio
async def test_new_scientific_bac_can_explicitly_choose_prepa(
    repository_factory,
) -> None:
    service = RecommendationService(
        _new_bac_catalogue(repository_factory),
        AlwaysEligible(),
    )

    decision = await service.recommend(
        SubjectState(
            profile=AcademicProfile.NEW_BAC,
            bac_specialty="MATH",
            target="PREPA",
        )
    )

    assert decision.primary is not None
    assert decision.primary.formation_code == "PREPA_GENERAL"


@pytest.mark.asyncio
async def test_scientific_bac_response_lists_licences_before_prepa(
    repository_factory,
) -> None:
    catalogue = _new_bac_catalogue(repository_factory)
    service = RecommendationService(catalogue, AlwaysEligible())
    subject = SubjectState(
        profile=AcademicProfile.NEW_BAC,
        bac_specialty="MATH",
    )
    decision = await service.recommend(subject)

    answer = await StructuredResponseBuilder(catalogue).orientation(subject, decision)

    assert answer is not None
    assert "je te recommande d'abord les licences IIT admissibles" in answer
    assert answer.index("Licence en Informatique") < answer.index(
        "Mécatronique & Systèmes Intelligents"
    )
    assert answer.index("Mécatronique & Systèmes Intelligents") < answer.index(
        "Cycle Préparatoire"
    )
    assert "conseil prioritaire" not in answer


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "profile",
    [AcademicProfile.PREPA_HOLDER, AcademicProfile.LICENCE_HOLDER],
)
async def test_completed_prepa_or_licence_still_targets_engineering(
    profile: AcademicProfile,
    repository_factory,
) -> None:
    service = RecommendationService(_catalogue(repository_factory), AlwaysEligible())

    decision = await service.recommend(SubjectState(profile=profile))

    assert decision.primary is not None
    assert decision.primary.formation_code == "INGENIEUR_INFO"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("subject", "expected"),
    [
        (
            SubjectState(
                profile=AcademicProfile.LICENCE_HOLDER,
                licence_specialty="INFORMATIQUE",
            ),
            "relevés de notes",
        ),
        (
            SubjectState(
                profile=AcademicProfile.LICENCE_STUDENT,
                licence_specialty="INFORMATIQUE",
            ),
            "entrée en deuxième année",
        ),
        (
            SubjectState(profile=AcademicProfile.PREPA_HOLDER),
            "suite logique est le cycle ingénieur",
        ),
        (
            SubjectState(profile=AcademicProfile.PREPA_STUDENT),
            "complément du cycle préparatoire",
        ),
    ],
)
async def test_orientation_explains_next_step_for_each_existing_profile(
    subject: SubjectState,
    expected: str,
    repository_factory,
) -> None:
    catalogue = _new_bac_catalogue(repository_factory)
    service = RecommendationService(catalogue, AlwaysEligible())
    decision = await service.recommend(subject)

    answer = await StructuredResponseBuilder(catalogue).orientation(subject, decision)

    assert answer is not None
    assert expected in answer


@pytest.mark.asyncio
async def test_in_progress_licence_states_validation_before_engineering(
    repository_factory,
) -> None:
    subject = SubjectState(
        profile=AcademicProfile.LICENCE_STUDENT,
        target="LICENCE",
        licence_specialty="INFORMATIQUE",
    )
    catalogue = _new_bac_catalogue(repository_factory)
    decision = await RecommendationService(catalogue, AlwaysEligible()).recommend(subject)

    answer = await StructuredResponseBuilder(catalogue).orientation(subject, decision)

    assert answer is not None
    assert "ta licence devra d'abord être validée" in answer
    assert "ce n'est pas une admission automatique" in answer


@pytest.mark.asyncio
async def test_incomplete_licence_profile_does_not_present_fake_specialisation(
    repository_factory,
) -> None:
    subject = SubjectState(
        profile=AcademicProfile.LICENCE_STUDENT,
        target="LICENCE",
        licence_specialty="INFORMATIQUE",
    )
    catalogue = _new_bac_catalogue(repository_factory)
    decision = await RecommendationService(catalogue, AlwaysEligible()).recommend(subject)

    answer = await StructuredResponseBuilder(catalogue).orientation(subject, decision)

    assert answer is not None
    assert "Pour personnaliser cette orientation" in answer
    assert "ta section de bac" in answer
    assert "Big Data & Analyse des Données" not in answer
    assert "Veux-tu voir le programme détaillé de cette formation ?" in answer


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
@pytest.mark.parametrize(
    ("bac", "expected_primary"),
    [
        ("MATH", "LICENCE_INFO"),
        ("SCIENCES", "LICENCE_INFO"),
        ("INFORMATIQUE", "LICENCE_INFO"),
        ("ECONOMIE_GESTION", "LICENCE_INFO"),
        ("TECHNIQUE", "LICENCE_MECATRONIQUE_SI"),
    ],
)
async def test_new_bac_business_priority_is_stable(
    bac: str,
    expected_primary: str,
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
    assert decision.primary.formation_code == expected_primary


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
