from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.academic.enums import FormationElementType
from app.domain.conversation.models import (
    AcademicProfile,
    ChatMessage,
    ConversationState,
    SubjectState,
)
from app.domain.recommendation.schemas import (
    EligibilityDecision,
    EligibilityStatus,
    RecommendationDecision,
    RecommendationOption,
)
from app.services.dialogue.orchestrator import ChatOrchestrator
from app.services.dialogue.structured_response import StructuredResponseBuilder
from app.services.academic.target_resolver import AcademicTarget


pytestmark = pytest.mark.unit


class EmptyLlm:
    async def generate(self, *args, **kwargs):
        del args, kwargs
        return ""


class TrackingLlm:
    def __init__(self) -> None:
        self.roles: list[str] = []

    async def generate(self, role, *args, **kwargs):
        del args, kwargs
        self.roles.append(role)
        return ""


def _formation() -> SimpleNamespace:
    return SimpleNamespace(
        id=20,
        parcours_id=2,
        code="LICENCE_INFO",
        nom="Licence en Informatique",
        intitule_diplome="Licence en Informatique",
        duree_annees=3,
        actif=True,
    )


def _cyber_specialisation() -> SimpleNamespace:
    return SimpleNamespace(
        id=201,
        formation_id=20,
        code="LIC_INFO_CYBER",
        nom="Cybersécurité et Réseaux",
        actif=True,
    )


def _catalogue(repository_factory, *, elements=(), tariffs=()):
    return SimpleNamespace(
        parcours=repository_factory(),
        formations=repository_factory([_formation()]),
        specialisations=repository_factory([_cyber_specialisation()]),
        elements=repository_factory(elements),
        tarifs=repository_factory(tariffs),
    )


def _registration_document(
    document_id: int,
    code: str,
    name: str,
    order: int,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=document_id,
        parcours_id=2,
        formation_id=None,
        specialisation_id=None,
        type_element=FormationElementType.DOCUMENT_INSCRIPTION,
        code=code,
        nom=name,
        ordre_affichage=order,
        actif=True,
    )


@pytest.mark.asyncio
async def test_affirmative_follow_up_continues_the_remembered_cyber_program(
    repository_factory,
) -> None:
    topic = SimpleNamespace(
        id=1,
        formation_id=20,
        specialisation_id=201,
        type_element=FormationElementType.CONTENU_PROGRAMME,
        nom="Sécurité des systèmes",
        description=None,
        actif=True,
    )
    catalogue = _catalogue(repository_factory, elements=[topic])
    orchestrator = ChatOrchestrator(
        catalogue=catalogue,
        eligibility=object(),  # type: ignore[arg-type]
        recommendation=object(),  # type: ignore[arg-type]
        rag=object(),  # type: ignore[arg-type]
        llm=EmptyLlm(),  # type: ignore[arg-type]
    )
    state = ConversationState.new(uuid4())
    state.history.append(ChatMessage(role="assistant", content="Veux-tu voir le programme ?"))
    subject = state.active_state
    subject.profile = AcademicProfile.NEW_BAC
    subject.bac_specialty = "ECONOMIE_GESTION"
    subject.recommended_offer = "LICENCE_INFO"
    subject.recommended_specialisation = "LIC_INFO_CYBER"
    subject.pending_action = "PROGRAMME"
    subject.last_intents = ["DIFFICULTY"]

    result = await orchestrator.process("ouiii", state)

    assert result.intents == ("PROGRAMME",)
    assert "Sécurité des systèmes" in result.answer
    assert "Je suis là pour continuer" not in result.answer


@pytest.mark.asyncio
async def test_fees_deduplicate_identical_rows_and_keep_languages(
    repository_factory,
) -> None:
    common = {
        "formation_id": 20,
        "specialisation_id": None,
        "frais_inscription": 800,
        "mensualite": 600,
        "nb_mensualites": 10,
        "devise": "TND",
        "annee_universitaire": "2026-2027",
        "statut": "CONFIRME",
        "actif": True,
    }
    tariffs = [
        SimpleNamespace(id=1, langue_enseignement="FRANCAIS", **common),
        SimpleNamespace(id=2, langue_enseignement="FRANCAIS", **common),
        SimpleNamespace(
            id=3,
            langue_enseignement="ANGLAIS",
            **{**common, "mensualite": 650},
        ),
    ]
    catalogue = _catalogue(repository_factory, tariffs=tariffs)
    builder = StructuredResponseBuilder(catalogue)

    answer = await builder.fees(AcademicTarget(_formation()))

    assert answer.count("• Licence en Informatique") == 2
    assert "(français · 2026-2027)" in answer
    assert "(anglais · 2026-2027)" in answer


@pytest.mark.asyncio
async def test_fees_without_target_ask_for_the_formation(repository_factory) -> None:
    answer = await StructuredResponseBuilder(_catalogue(repository_factory)).fees(None)

    assert "indique-moi la formation" in answer
    assert "Tarifs publics" not in answer


@pytest.mark.asyncio
async def test_all_program_topics_are_kept_for_an_explicit_all_request(
    repository_factory,
) -> None:
    topics = [
        SimpleNamespace(
            id=index,
            formation_id=20,
            specialisation_id=201,
            type_element=FormationElementType.CONTENU_PROGRAMME,
            nom=f"Matière {index}",
            description=None,
            actif=True,
        )
        for index in range(1, 11)
    ]
    catalogue = _catalogue(repository_factory, elements=topics)

    answer = await StructuredResponseBuilder(catalogue).formation_details(
        AcademicTarget(_formation(), _cyber_specialisation()),
        ["PROGRAMME"],
        include_all=True,
    )

    assert "Matière 1" in answer
    assert "Matière 10" in answer
    assert "certification" not in answer.casefold()
    assert "débouché" not in answer.casefold()


@pytest.mark.asyncio
async def test_all_program_follow_up_keeps_the_remembered_specialisation(
    repository_factory,
) -> None:
    topics = [
        SimpleNamespace(
            id=index,
            formation_id=20,
            specialisation_id=201,
            type_element=FormationElementType.CONTENU_PROGRAMME,
            nom=f"Matière {index}",
            description=None,
            actif=True,
        )
        for index in range(1, 11)
    ]
    catalogue = _catalogue(repository_factory, elements=topics)
    orchestrator = ChatOrchestrator(
        catalogue=catalogue,
        eligibility=object(),  # type: ignore[arg-type]
        recommendation=object(),  # type: ignore[arg-type]
        rag=object(),  # type: ignore[arg-type]
        llm=EmptyLlm(),  # type: ignore[arg-type]
    )
    state = ConversationState.new(uuid4())
    state.history.append(ChatMessage(role="assistant", content="Voici la spécialisation."))
    subject = state.active_state
    subject.profile = AcademicProfile.NEW_BAC
    subject.bac_specialty = "MATH"
    subject.recommended_offer = "LICENCE_INFO"
    subject.recommended_specialisation = "LIC_INFO_CYBER"

    result = await orchestrator.process(
        "atini les matieres el kol elli na9rahom",
        state,
    )

    assert result.intents == ("PROGRAMME",)
    assert "Cybersécurité et Réseaux" in result.answer
    assert "Matière 10" in result.answer


@pytest.mark.asyncio
async def test_registration_documents_are_resolved_from_the_formation_pathway(
    repository_factory,
) -> None:
    documents = [
        _registration_document(1, "DOC_BAC", "Copie conforme du Bac", 10),
        _registration_document(2, "DOC_CIN", "Copie CIN", 20),
        _registration_document(3, "DOC_PREINSCRIPTION", "Pré-inscription", 30),
    ]
    catalogue = _catalogue(repository_factory)
    catalogue.elements.list_applicable = AsyncMock(return_value=documents)

    answer = await StructuredResponseBuilder(catalogue).registration_documents(
        AcademicTarget(_formation(), _cyber_specialisation()),
        pre_registration_completed=True,
    )

    assert "déjà effectué la pré-inscription" in answer
    assert "• Copie conforme du Bac" in answer
    assert "• Copie CIN" in answer
    assert "• Pré-inscription" not in answer
    catalogue.elements.list_applicable.assert_awaited_once_with(
        parcours_id=2,
        formation_id=20,
        specialisation_id=201,
        element_types=(FormationElementType.DOCUMENT_INSCRIPTION,),
        include_inactive=False,
    )


@pytest.mark.asyncio
async def test_completed_pre_registration_routes_to_documents_without_llm(
    repository_factory,
) -> None:
    documents = [
        _registration_document(1, "DOC_BAC", "Copie conforme du Bac", 10),
        _registration_document(2, "DOC_CIN", "Copie CIN", 20),
        _registration_document(3, "DOC_PREINSCRIPTION", "Pré-inscription", 30),
    ]
    catalogue = _catalogue(repository_factory)
    catalogue.elements.list_applicable = AsyncMock(return_value=documents)
    orchestrator = ChatOrchestrator(
        catalogue=catalogue,
        eligibility=object(),  # type: ignore[arg-type]
        recommendation=object(),  # type: ignore[arg-type]
        rag=object(),  # type: ignore[arg-type]
        llm=EmptyLlm(),  # type: ignore[arg-type]
    )
    state = ConversationState.new(uuid4())
    state.history.append(ChatMessage(role="assistant", content="Préinscription proposée."))
    subject = state.active_state
    subject.profile = AcademicProfile.NEW_BAC
    subject.bac_specialty = "ECONOMIE_GESTION"
    subject.recommended_offer = "LICENCE_INFO"
    subject.recommended_specialisation = "LIC_INFO_CYBER"

    result = await orchestrator.process(
        "3amlt preinscrit chnouma laxra9 mtaa inscription",
        state,
    )

    assert result.intents == ("REGISTRATION_DOCUMENTS",)
    assert "• Copie conforme du Bac" in result.answer
    assert "• Copie CIN" in result.answer
    assert "• Pré-inscription" not in result.answer
    assert "http" not in result.answer
    assert subject.pre_registration_completed is True


def test_profile_recall_answers_without_recommending_again(repository_factory) -> None:
    del repository_factory
    subject = SubjectState(
        profile=AcademicProfile.NEW_BAC,
        bac_specialty="ECONOMIE_GESTION",
    )

    answer = StructuredResponseBuilder.profile_summary(subject)

    assert answer == "Tu m'as indiqué avoir un bac Économie et Gestion."
    assert "recommande" not in answer


def test_unavailable_licence_uses_only_the_rule_based_recommendation() -> None:
    eligibility = EligibilityDecision(
        EligibilityStatus.ELIGIBLE,
        20,
        "LICENCE_INFO",
    )
    option = RecommendationOption(
        20,
        "LICENCE_INFO",
        "Licence en Informatique",
        None,
        None,
        None,
        1.0,
        eligibility,
    )
    subject = SubjectState(
        profile=AcademicProfile.NEW_BAC,
        bac_specialty="ECONOMIE_GESTION",
    )

    answer = StructuredResponseBuilder.unavailable_formation(
        "licence industrielle",
        subject,
        RecommendationDecision(option, None),
    )

    assert "ne figure pas dans le catalogue" in answer
    assert "Licence en Informatique" in answer
    assert "licence en Ingénierie Industrielle" not in answer


def test_bac_letters_without_rule_never_receives_an_invented_formation() -> None:
    subject = SubjectState(
        profile=AcademicProfile.NEW_BAC,
        bac_specialty="LETTERS",
    )

    answer = StructuredResponseBuilder.unavailable_formation(
        "licence lettres",
        subject,
        RecommendationDecision(None, None),
    )

    assert "aucune formation IIT" in answer
    assert "Licence en Lettres" not in answer


@pytest.mark.asyncio
async def test_unknown_licence_request_never_reaches_the_final_llm(
    repository_factory,
) -> None:
    catalogue = _catalogue(repository_factory)
    eligibility = EligibilityDecision(
        EligibilityStatus.ELIGIBLE,
        20,
        "LICENCE_INFO",
    )
    option = RecommendationOption(
        20,
        "LICENCE_INFO",
        "Licence en Informatique",
        None,
        None,
        None,
        1.0,
        eligibility,
    )
    recommendation = SimpleNamespace(
        recommend=AsyncMock(return_value=RecommendationDecision(option, None))
    )
    llm = TrackingLlm()
    orchestrator = ChatOrchestrator(
        catalogue=catalogue,
        eligibility=object(),  # type: ignore[arg-type]
        recommendation=recommendation,  # type: ignore[arg-type]
        rag=object(),  # type: ignore[arg-type]
        llm=llm,  # type: ignore[arg-type]
    )
    state = ConversationState.new(uuid4())
    state.history.append(ChatMessage(role="assistant", content="Parlons de ton orientation."))
    state.active_state.profile = AcademicProfile.NEW_BAC
    state.active_state.bac_specialty = "ECONOMIE_GESTION"

    result = await orchestrator.process(
        "beeh aleh manjmch naml licence industrielle ?",
        state,
    )

    assert result.intents == ("ORIENTATION",)
    assert "ne figure pas dans le catalogue" in result.answer
    assert "Licence en Informatique" in result.answer
    assert "licence en Ingénierie Industrielle" not in result.answer
    assert state.active_state.licence_specialty is None
    assert "final" not in llm.roles
