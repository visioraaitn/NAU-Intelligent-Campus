"""Regression cases derived from observed IIT conversation failures."""
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from app.domain.academic.enums import FormationElementType as Kind
from app.domain.conversation.models import ConversationState, AcademicProfile
from app.domain.recommendation.schemas import RecommendationDecision, EligibilityDecision, EligibilityStatus
from app.services.dialogue.esprit_nlu import DomainClassification, SemanticUnderstanding
from app.services.dialogue.turn_gate import TurnGate, TurnType
from app.services.dialogue.intent_detector import IntentDetector
from app.services.dialogue.contextual_modifier import ContextScope
from app.services.dialogue.dialogue_act_detector import DialogueAct
from app.services.dialogue.pending_slot_resolver import PendingSlotResolver
from app.services.dialogue.orchestrator import ChatOrchestrator

@pytest.mark.parametrize('message,expected', [
    ('tarifs', {'FEES'}), ('w les certif elli nekhdhouhom', {'CERTIFICATIONS'}),
    ('wel formulaire mtaa el preiscrit', {'PREINSCRIPTION'}),
    ('Bh el diplôme mbaad mitaref bih?', {'ACCREDITATION'}),
    ('fiha stage walla ?', {'INTERNSHIPS'}),
    ('les projets et la pratique', {'PROJECTS','PRACTICE'}),
    ('Quels projets et stages en architecture ?', {'PROJECTS','INTERNSHIPS'}),
    ('preinscrit et les documents du dossier', {'PREINSCRIPTION','REGISTRATION_DOCUMENTS'}),
    ('chnowa nejem na9ra fel iit ?', {'CATALOG'}),
    ('nheb naaref lprogramme mte3 l iit', {'CATALOG'}),
    ('licence', {'CATALOG'}),
    ('ena 9rit fel iset nejem nkammel na9ra fel iit génie industriel', {'ADMISSION'}),
    ('nheb nzid naraf les matiere el koll w les certif fiha pratique wella w nejjem nel9a biha khedma ?', {'PROGRAMME','CERTIFICATIONS','PRACTICE','CAREERS'}),
])
def test_observed_questions_retain_all_requested_topics(message, expected):
    assert TurnGate().classify(message) is TurnType.ACADEMIC
    actual=IntentDetector().detect(message,previous=(),scope=ContextScope.CURRENT,dialogue_act=DialogueAct.ASK_INFORMATION,slot_parsed=False)
    assert expected <= set(actual)

@pytest.mark.parametrize('confirmation',['ay','ayh','ey','oui','bh ay'])
def test_short_confirmation_continues_only_pending_action(confirmation):
    subject=ConversationState.new(uuid4()).active_state
    subject.pending_action='PREINSCRIPTION'
    assert PendingSlotResolver().resolve(confirmation,subject).forced_intents==('PREINSCRIPTION',)
    assert PendingSlotResolver().resolve(confirmation,subject).forced_intents==()


def test_delayed_profile_answer_does_not_resume_registration():
    subject=ConversationState.new(uuid4()).active_state
    subject.pending_slot='PROFILE'
    subject.last_intents=['PREINSCRIPTION']
    subject.profile=AcademicProfile.NEW_BAC
    assert PendingSlotResolver().resolve('ena bac lettre',subject).previous_intents==('ORIENTATION',)


@pytest.fixture
def audit_bot(repository_factory):
    formation=SimpleNamespace(id=20,parcours_id=2,code='LICENCE_INFO',nom='Licence en Informatique',intitule_diplome='Licence en Informatique',duree_annees=3,actif=True)
    def element(id,kind,nom,description=None):
        return SimpleNamespace(id=id,formation_id=20,specialisation_id=None,type_element=kind,nom=nom,description=description,actif=True)
    catalogue=SimpleNamespace(
        formations=repository_factory([formation]),specialisations=repository_factory(),parcours=repository_factory(),
        elements=repository_factory([element(1,Kind.CONTENU_PROGRAMME,'Programmation'),element(2,Kind.CERTIFICATION,'ISTQB'),element(3,Kind.INFORMATION,'Projets académiques','Projet Tutoré et Projet Fédéré'),element(4,Kind.MOBILITE,'Stage international en entreprise')]),
        tarifs=repository_factory(),accreditations=repository_factory(),orientation_rules=repository_factory(),
    )
    llm=AsyncMock();llm.generate.return_value=''
    bot=ChatOrchestrator(catalogue=catalogue,eligibility=AsyncMock(),recommendation=AsyncMock(),rag=AsyncMock(),llm=llm)
    bot.recommendation_service.recommend.return_value=RecommendationDecision(None,None)
    return bot,llm

@pytest.mark.asyncio
async def test_direct_multitopic_question_answers_every_axis_without_llm(audit_bot):
    bot,llm=audit_bot
    response=await bot.process('licence informatique : programme, certif, pratique, projets et stages ?',ConversationState.new(uuid4()))
    for term in ['Programmation','ISTQB','Projet Tutoré','Stages','Stage international']:
        assert term in response.answer
    llm.generate.assert_not_called()

@pytest.mark.asyncio
async def test_fees_and_programme_are_not_replaced_by_one_axis(audit_bot):
    bot,_=audit_bot
    response=await bot.process('licence informatique : frais et programme ?',ConversationState.new(uuid4()))
    assert 'Programmation' in response.answer
    assert 'tarif' in response.answer.lower()

@pytest.mark.asyncio
async def test_profile_question_does_not_hide_requested_catalogue_fact(audit_bot):
    bot,_=audit_bot
    response=await bot.process('conseille moi une formation et donne les tarifs',ConversationState.new(uuid4()))
    assert 'tarif' in response.answer.lower() or 'frais' in response.answer.lower()
    assert 'où tu en es' in response.answer


@pytest.mark.asyncio
async def test_darija_orientation_survives_incorrect_domain_model(audit_bot):
    bot,_=audit_bot
    bot.esprit.classify_domain=AsyncMock(return_value=DomainClassification('OUT_OF_SCOPE',.99))
    state=ConversationState.new(uuid4())
    response=await bot.process('nhebek tensahni',state)
    assert 'ORIENTATION' in response.intents
    await bot.process('mazelt ki njaht bac',state)
    response=await bot.process('eco',state)
    assert 'OUT_OF_SCOPE' not in response.intents
    assert state.active_state.bac_specialty
    bot.esprit.classify_domain.assert_not_called()


@pytest.mark.asyncio
async def test_ineligible_admission_keeps_programme_answer(audit_bot):
    bot,_=audit_bot
    bot.eligibility_service.evaluate.return_value=EligibilityDecision(EligibilityStatus.NOT_ELIGIBLE,20,'LICENCE_INFO')
    response=await bot.process('licence informatique : admission et programme ?',ConversationState.new(uuid4()))
    assert 'Programmation' in response.answer
    assert 'admission' in response.answer.lower()


@pytest.mark.asyncio
async def test_all_paths_request_survives_profile_question(audit_bot):
    bot,_=audit_bot
    bot.eligibility_service.evaluate.return_value=EligibilityDecision(EligibilityStatus.ELIGIBLE,20,'LICENCE_INFO')
    state=ConversationState.new(uuid4())
    await bot.process('Quels sont tous les parcours que je peux faire ?',state)
    response=await bot.process('je viens de réussir mon bac math',state)
    assert 'Licence en Informatique' in response.answer
    assert 'ne garantit pas' in response.answer


@pytest.mark.asyncio
async def test_unknown_spelling_is_understood_semantically(audit_bot):
    bot,_=audit_bot
    bot.esprit.understand=AsyncMock(return_value=SemanticUnderstanding(
        DomainClassification('SOCIAL',.97), 'Comment ça va ?', (), 'HOW_ARE_YOU'))
    response=await bot.process('komentutvaa',ConversationState.new(uuid4()))
    assert 'Ça va' in response.answer
    bot.esprit.understand.assert_awaited_once()


@pytest.mark.parametrize('message',['cvn','cvnn','cvnnnnnn','cvaaa','salllemmm'])
def test_repeated_letters_use_dynamic_similarity(message):
    assert TurnGate().classify(message) in {TurnType.HOW_ARE_YOU,TurnType.GREETING}


@pytest.mark.asyncio
async def test_semantic_topics_route_without_pattern_match(audit_bot):
    bot,_=audit_bot
    bot.esprit.understand=AsyncMock(return_value=SemanticUnderstanding(
        DomainClassification('IN_SCOPE',.96,True), 'Les projets et stages en licence informatique', ('PROJECTS','INTERNSHIPS')))
    response=await bot.process('stg w prjts',ConversationState.new(uuid4()))
    assert 'Projet Tutoré' in response.answer and 'Stage international' in response.answer
    assert set(response.intents)=={'PROJECTS','INTERNSHIPS'}


@pytest.mark.asyncio
async def test_pending_confirmation_does_not_reach_domain_model(audit_bot):
    bot,_=audit_bot
    bot.esprit.understand=AsyncMock(side_effect=AssertionError('No semantic lookup needed'))
    bot.esprit.classify_domain=AsyncMock(side_effect=AssertionError('No domain lookup needed'))
    state=ConversationState.new(uuid4())
    state.active_state.pending_action='PROGRAMME'
    state.active_state.recommended_offer='LICENCE_INFO'
    response=await bot.process('ay',state)
    assert 'Programmation' in response.answer
    bot.esprit.understand.assert_not_called()
    bot.esprit.classify_domain.assert_not_called()
