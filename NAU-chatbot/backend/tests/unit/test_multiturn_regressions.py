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
from app.services.dialogue.esprit_nlu import EspritNluService
from app.services.llm.providers import LLMMessage
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


class DomainAwareLlm:
    def __init__(self, label: str, confidence: float, iit_signal: bool) -> None:
        self.label = label
        self.confidence = confidence
        self.iit_signal = iit_signal
        self.roles: list[str] = []

    async def generate(self, role, messages, *, max_new_tokens):
        del max_new_tokens
        self.roles.append(role)
        if role == "esprit" and "Tu classes le MESSAGE" in messages[0].content:
            return (
                '{"label":"' + self.label + '","confidence":'
                + str(self.confidence).lower()
                + ',"iit_signal":'
                + str(self.iit_signal).lower()
                + "}"
            )
        if role == "esprit":
            return ""
        raise AssertionError("the final generator must not be called in this scenario")


@pytest.mark.asyncio
async def test_domain_classifier_accepts_strict_model_json() -> None:
    class DomainLlm:
        async def generate(self, role, messages, *, max_new_tokens):
            assert role == "esprit"
            assert isinstance(messages[0], LLMMessage)
            assert max_new_tokens == 60
            return '{"label":"OUT_OF_SCOPE","confidence":0.98,"iit_signal":false}'

    result = await EspritNluService(DomainLlm()).classify_domain("chnou ta9s taw")

    assert result.label == "OUT_OF_SCOPE"
    assert result.confidence == 0.98
    assert result.iit_signal is False


@pytest.mark.asyncio
async def test_domain_classifier_handles_invalid_model_output_conservatively() -> None:
    class DomainLlm:
        async def generate(self, role, messages, *, max_new_tokens):
            del role, messages, max_new_tokens
            return "Je ne suis pas certain."

    with pytest.raises(ValueError):
        await EspritNluService(DomainLlm()).classify_domain("question inconnue")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("label", "confidence", "message", "expected"),
    [
        ("OUT_OF_SCOPE", 0.0, "écris un programme Python", "pas suffisamment compris"),
        ("UNCLEAR", 0.0, "blabla truc machin", "pas suffisamment compris"),
        ("OUT_OF_SCOPE", 0.99, "quelle est la politique actuelle ?", "uniquement"),
    ],
)
async def test_uncertain_or_external_messages_never_reach_final_generation(
    repository_factory,
    label,
    confidence,
    message,
    expected,
) -> None:
    llm = DomainAwareLlm(label, confidence, False)
    orchestrator = ChatOrchestrator(
        catalogue=_catalogue(repository_factory),
        eligibility=object(),  # type: ignore[arg-type]
        recommendation=object(),  # type: ignore[arg-type]
        rag=object(),  # type: ignore[arg-type]
        llm=llm,  # type: ignore[arg-type]
    )

    result = await orchestrator.process(message, ConversationState.new(uuid4()))

    assert expected in result.answer
    assert "final" not in llm.roles


@pytest.mark.asyncio
async def test_in_scope_follow_up_without_repeated_iit_word_keeps_context(
    repository_factory,
) -> None:
    llm = DomainAwareLlm("IN_SCOPE", 0.8, False)
    orchestrator = ChatOrchestrator(
        catalogue=_catalogue(repository_factory),
        eligibility=object(),  # type: ignore[arg-type]
        recommendation=object(),  # type: ignore[arg-type]
        rag=object(),  # type: ignore[arg-type]
        llm=llm,  # type: ignore[arg-type]
    )
    state = ConversationState.new(uuid4())
    state.history.append(ChatMessage(role="assistant", content="Voici la licence informatique."))
    state.active_state.recommended_offer = "LICENCE_INFO"
    state.active_state.recommended_specialisation = "LIC_INFO_CYBER"

    result = await orchestrator.process("quelles sont les spécialités ?", state)

    assert result.intents == ("DETAILS",)
    assert result.answer.startswith("Licence en Informatique")
    assert "Cybersécurité et Réseaux" in result.answer
    assert "uniquement" not in result.answer
    assert "final" not in llm.roles


@pytest.mark.asyncio
async def test_pre_registration_follow_up_reuses_remembered_target_without_llm(
    repository_factory,
) -> None:
    catalogue = _catalogue(repository_factory)
    eligibility = SimpleNamespace(
        evaluate=AsyncMock(
            return_value=EligibilityDecision(
                EligibilityStatus.ELIGIBLE,
                20,
                "LICENCE_INFO",
            )
        )
    )
    recommendation = SimpleNamespace(
        recommend=AsyncMock(return_value=RecommendationDecision(None, None))
    )
    llm = TrackingLlm()
    orchestrator = ChatOrchestrator(
        catalogue=catalogue,
        eligibility=eligibility,  # type: ignore[arg-type]
        recommendation=recommendation,  # type: ignore[arg-type]
        rag=object(),  # type: ignore[arg-type]
        llm=llm,  # type: ignore[arg-type]
    )
    state = ConversationState.new(uuid4())
    state.history.append(ChatMessage(role="assistant", content="Voici la licence informatique."))
    subject = state.active_state
    subject.profile = AcademicProfile.NEW_BAC
    subject.bac_specialty = "ECONOMIE_GESTION"
    subject.recommended_offer = "LICENCE_INFO"

    result = await orchestrator.process(
        "nice beeh atini kifeh naml preinscrit",
        state,
    )

    assert result.intents == ("PREINSCRIPTION",)
    assert "pré-inscription suivie du dossier" in result.answer
    assert "https://iit.tn/admission/" in result.answer
    assert "final" not in llm.roles


@pytest.mark.asyncio
async def test_short_specialisation_choice_stays_inside_active_formation(
    repository_factory,
) -> None:
    formation = SimpleNamespace(
        id=50,
        parcours_id=3,
        code="INGENIEUR_INFO",
        nom="Génie Informatique",
        intitule_diplome="Diplôme National d'Ingénieur en Génie Informatique",
        duree_annees=3,
        actif=True,
    )
    glid = SimpleNamespace(
        id=501,
        formation_id=50,
        code="GLID",
        nom="Génie Logiciel et Informatique Décisionnelle",
        actif=True,
    )

    class Catalogue:
        parcours = repository_factory()
        formations = repository_factory([formation])
        specialisations = repository_factory([glid])
        elements = repository_factory()
        tarifs = repository_factory()
        accreditations = repository_factory()

        async def get_formation(self, formation_id: int):
            return await self.formations.require(formation_id)

    llm = TrackingLlm()
    orchestrator = ChatOrchestrator(
        catalogue=Catalogue(),  # type: ignore[arg-type]
        eligibility=object(),  # type: ignore[arg-type]
        recommendation=object(),  # type: ignore[arg-type]
        rag=object(),  # type: ignore[arg-type]
        llm=llm,  # type: ignore[arg-type]
    )
    state = ConversationState.new(uuid4())
    state.history.append(ChatMessage(role="assistant", content="Choisis une spécialité."))
    state.active_state.recommended_offer = "INGENIEUR_INFO"

    result = await orchestrator.process("genie logicielleeee", state)

    assert result.intents == ("DETAILS",)
    assert result.answer.startswith("Génie Logiciel et Informatique Décisionnelle")
    assert "Licence en Informatique" not in result.answer
    assert "final" not in llm.roles


@pytest.mark.asyncio
async def test_strong_academic_wording_overrides_wrong_domain_label(
    repository_factory,
) -> None:
    llm = DomainAwareLlm("OUT_OF_SCOPE", 0.9, False)
    orchestrator = ChatOrchestrator(
        catalogue=_catalogue(repository_factory),
        eligibility=object(),  # type: ignore[arg-type]
        recommendation=object(),  # type: ignore[arg-type]
        rag=object(),  # type: ignore[arg-type]
        llm=llm,  # type: ignore[arg-type]
    )

    result = await orchestrator.process(
        "slm nejjem na9ra bel lil ?",
        ConversationState.new(uuid4()),
    )

    assert result.intents == ("SCHEDULE",)
    assert "cours du soir" in result.answer
    assert not result.answer.startswith("Salut")
    assert "final" not in llm.roles


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


def _catalogue(repository_factory, *, elements=(), tariffs=(), accreditations=()):
    return SimpleNamespace(
        parcours=repository_factory(),
        formations=repository_factory([_formation()]),
        specialisations=repository_factory([_cyber_specialisation()]),
        elements=repository_factory(elements),
        tarifs=repository_factory(tariffs),
        accreditations=repository_factory(accreditations),
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
async def test_location_names_both_iit_sites_and_admin_contact(repository_factory) -> None:
    answer = await StructuredResponseBuilder(_catalogue(repository_factory)).location()

    assert "Technopole El Ons" in answer
    assert "Route Mharza" in answer
    assert "cours du soir" in answer
    assert "info@iit.tn" in answer


@pytest.mark.asyncio
async def test_evening_schedule_does_not_invent_hours(repository_factory) -> None:
    answer = await StructuredResponseBuilder(_catalogue(repository_factory)).schedule()

    assert "pas suffisamment documentés" in answer
    assert "70 28 26 00" in answer
    assert "19h" not in answer


@pytest.mark.asyncio
async def test_all_licence_fees_exclude_non_licence_formations(repository_factory) -> None:
    prepa = SimpleNamespace(
        id=30,
        parcours_id=1,
        code="PREPA_GENERAL",
        nom="Cycle Préparatoire",
        actif=True,
    )
    licence_tariff = SimpleNamespace(
        id=1,
        formation_id=20,
        specialisation_id=None,
        frais_inscription=800,
        mensualite=600,
        nb_mensualites=10,
        devise="TND",
        actif=True,
    )
    prepa_tariff = SimpleNamespace(
        id=2,
        formation_id=30,
        specialisation_id=None,
        frais_inscription=900,
        mensualite=700,
        nb_mensualites=10,
        devise="TND",
        actif=True,
    )
    catalogue = _catalogue(repository_factory, tariffs=[licence_tariff, prepa_tariff])
    catalogue.formations = repository_factory([_formation(), prepa])

    answer = await StructuredResponseBuilder(catalogue).fees(
        None,
        include_all=True,
        licence_only=True,
    )

    assert "Licence en Informatique" in answer
    assert "Cycle Préparatoire" not in answer


@pytest.mark.asyncio
async def test_iso_question_only_returns_institutional_iso_status(repository_factory) -> None:
    accreditation = SimpleNamespace(
        id=1,
        formation_id=20,
        code="EURO-INF",
        nom="EURO-INF",
        organisme="ASIIN",
        actif=True,
    )
    certification = SimpleNamespace(
        id=99,
        formation_id=None,
        specialisation_id=None,
        type_element=FormationElementType.CERTIFICATION,
        nom="ISO 21001",
        actif=True,
    )
    catalogue = _catalogue(
        repository_factory,
        elements=[certification],
        accreditations=[accreditation],
    )

    answer = await StructuredResponseBuilder(catalogue).accreditation(None, "ISO 21001")

    assert "ISO 21001 est enregistrée" in answer
    assert "EURO-INF" not in answer
    assert "Licence en Informatique" not in answer


@pytest.mark.asyncio
async def test_accreditation_answer_distinguishes_programme_label_and_iso_claim(
    repository_factory,
) -> None:
    accreditation = SimpleNamespace(
        id=1,
        formation_id=20,
        code="EURO-INF",
        nom="EURO-INF",
        organisme="ASIIN",
        description="Accréditation de programme international.",
        actif=True,
    )
    catalogue = _catalogue(repository_factory, accreditations=[accreditation])
    answer = await StructuredResponseBuilder(catalogue).accreditation(
        AcademicTarget(_formation()),
        "Le diplôme est-il reconnu ISO 21001 ?",
    )

    assert "EURO-INF" in answer
    assert "ASIIN" in answer
    assert "ISO 21001 n'est pas documentée" in answer
    assert "équivalence" in answer


@pytest.mark.asyncio
async def test_institutional_advantages_are_limited_and_non_guaranteeing(
    repository_factory,
) -> None:
    answer = await StructuredResponseBuilder(_catalogue(repository_factory)).institutional_advantages()

    assert "mobilité" in answer
    assert "accréditations de programmes enregistrées" in answer
    assert "ne garantissent ni l'admission" in answer


def test_profile_context_can_be_omitted_for_non_orientation_generation(
    repository_factory,
) -> None:
    from app.services.dialogue.known_facts_builder import KnownFactsBuilder

    subject = SubjectState(
        profile=AcademicProfile.NEW_BAC,
        bac_specialty="MATH",
    )

    known, _ = KnownFactsBuilder().build(subject, include_profile=False)

    assert "Situation actuelle" not in known
    assert "Mathématiques" not in known


@pytest.mark.asyncio
async def test_accreditation_includes_operator_supplied_iso_claim_without_verifying_it(
    repository_factory,
) -> None:
    certification = SimpleNamespace(
        id=99,
        formation_id=None,
        specialisation_id=None,
        type_element=FormationElementType.CERTIFICATION,
        code="CERT_ISO_21001",
        nom="ISO 21001",
        description="Déclaration opérateur à confirmer.",
        actif=True,
    )
    catalogue = _catalogue(repository_factory, elements=[certification])
    answer = await StructuredResponseBuilder(catalogue).accreditation(
        AcademicTarget(_formation()),
        "IIT est-elle certifiée ISO 21001 ?",
    )

    assert "ISO 21001" in answer
    assert "doit être confirmée" in answer
    assert "n'est pas documentée" not in answer


@pytest.mark.asyncio
async def test_bac_denial_asks_for_current_level_instead_of_assuming_bac(
    repository_factory,
) -> None:
    recommendation = SimpleNamespace(recommend=AsyncMock(return_value=SimpleNamespace(primary=None, alternatives=())))
    catalogue = _catalogue(repository_factory)
    orchestrator = ChatOrchestrator(
        catalogue=catalogue,
        eligibility=object(),  # type: ignore[arg-type]
        recommendation=recommendation,  # type: ignore[arg-type]
        rag=object(),  # type: ignore[arg-type]
        llm=EmptyLlm(),  # type: ignore[arg-type]
    )

    result = await orchestrator.process("manich bac", ConversationState.new(uuid4()))

    assert "où tu en es actuellement" in result.answer
    assert "Tu as un bac" not in result.answer


@pytest.mark.asyncio
async def test_completed_prepa_orientation_does_not_recommend_prepa_again(
    repository_factory,
) -> None:
    catalogue = _catalogue(repository_factory)
    recommendation = SimpleNamespace(
        recommend=AsyncMock(
            return_value=SimpleNamespace(
                primary=SimpleNamespace(
                    formation_code="INGENIEUR_INFO",
                    formation_id=20,
                    specialisation_code=None,
                    specialisation_id=None,
                    formation_name="Génie Informatique",
                    specialisation_name=None,
                ),
                alternatives=(),
            )
        )
    )
    orchestrator = ChatOrchestrator(
        catalogue=catalogue,
        eligibility=object(),  # type: ignore[arg-type]
        recommendation=recommendation,  # type: ignore[arg-type]
        rag=object(),  # type: ignore[arg-type]
        llm=EmptyLlm(),  # type: ignore[arg-type]
    )
    state = ConversationState.new(uuid4())
    state.active_state.profile = AcademicProfile.PREPA_HOLDER
    state.active_state.target = "ENGINEERING"

    result = await orchestrator.process(
        "j'ai terminé la prépa et je veux continuer mes études",
        state,
    )

    assert "Préparatoire" not in result.answer


@pytest.mark.asyncio
async def test_completed_prepa_clears_old_prepa_target_before_new_tariff_question(
    repository_factory,
) -> None:
    catalogue = _catalogue(repository_factory)
    orchestrator = ChatOrchestrator(
        catalogue=catalogue,
        eligibility=object(),  # type: ignore[arg-type]
        recommendation=object(),  # type: ignore[arg-type]
        rag=object(),  # type: ignore[arg-type]
        llm=EmptyLlm(),  # type: ignore[arg-type]
    )
    state = ConversationState.new(uuid4())
    subject = state.active_state
    subject.profile = AcademicProfile.PREPA_HOLDER
    subject.recommended_offer = "PREPA_GENERAL"

    await orchestrator.process(
        "j'ai terminé la prépa et je veux continuer mes études",
        state,
    )

    assert subject.recommended_offer is None


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
@pytest.mark.parametrize(
    ("message", "expected_topic"),
    [
        ("atini les matieres el kol elli na9rahom", "Matière 10"),
        ("chnouma les matiere elli najem narahom", "Matière 1"),
        ("chna9ra fi hal option", "Matière 1"),
    ],
)
async def test_all_program_follow_up_keeps_the_remembered_specialisation(
    repository_factory,
    message,
    expected_topic,
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

    result = await orchestrator.process(message, state)

    assert result.intents == ("PROGRAMME",)
    assert "Cybersécurité et Réseaux" in result.answer
    assert expected_topic in result.answer


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
