from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.conversation.models import AcademicProfile, ConversationState
from app.services.dialogue.esprit_nlu import DomainClassification, SemanticUnderstanding
from app.services.eligibility.eligibility_service import EligibilityService
from tests.unit.test_conversation_audit import audit_bot


@pytest.fixture
def industrial_bot(audit_bot):
    bot, llm = audit_bot
    bot.catalogue.formations.items.append(SimpleNamespace(
        id=40, parcours_id=3, code='INGENIEUR_INDUSTRIEL', nom='Génie Industriel',
        intitule_diplome="Diplôme National d'Ingénieur en Génie Industriel", duree_annees=3, actif=True))
    bot.catalogue.orientation_rules.items.append(SimpleNamespace(
        id=41, formation_id=40, specialisation_id=None, type_regle='ADMISSION', actif=True,
        criteres={'diplome_origine': {'in': ['LICENCE_MAINTENANCE_INDUSTRIELLE', 'LOGISTIQUE_INDUSTRIELLE']}},
        code='ADMISSION_INDUS', source_ref=None, description='Diplômes publiés'))
    return bot, llm


@pytest.mark.asyncio
async def test_unknown_repeated_letters_get_fast_clarification(audit_bot):
    bot, llm = audit_bot
    result = await bot.process('aaa', ConversationState.new(uuid4()))
    assert "pas compris" in result.answer
    llm.generate.assert_not_called()


@pytest.mark.asyncio
async def test_one_word_programme_asks_for_formation_without_model_delay(audit_bot):
    bot, llm = audit_bot
    result = await bot.process('programme', ConversationState.new(uuid4()))
    assert "nom de la formation" in result.answer
    llm.generate.assert_not_called()


@pytest.mark.asyncio
async def test_identity_question_is_answered_when_understood_semantically(audit_bot):
    bot, _ = audit_bot
    bot.esprit.understand = AsyncMock(return_value=SemanticUnderstanding(
        DomainClassification('SOCIAL', .95), '', (), 'IDENTITY'))
    result = await bot.process('tw enti chkoun', ConversationState.new(uuid4()))
    assert "assistant virtuel de l'IIT" in result.answer


@pytest.mark.asyncio
async def test_original_indus_thread_clarifies_instead_of_repeating_failure(industrial_bot):
    bot, llm = industrial_bot
    state = ConversationState.new(uuid4())
    first = await bot.process('ena licence indus', state)
    assert 'intitulé exact' in first.answer and 'logistique industrielle' in first.answer
    goal = await bot.process('ena nheb nakra ingenieur', state)
    assert 'tu vises un cycle ingénieur' in goal.answer
    assert goal.answer != first.answer
    validated = await bot.process('njaht licence', state)
    assert 'licence est validée' in validated.answer
    contradiction = await bot.process('ena njaht bac', state)
    assert 'correction de ton niveau actuel' in contradiction.answer
    assert state.active_state.profile is AcademicProfile.LICENCE_HOLDER
    bot.esprit.understand_credential = AsyncMock(return_value='INDUSTRIELLE')
    clarified = await bot.process("indus c'est industrielle", state)
    assert 'quelle spécialité précise' in clarified.answer
    assert state.active_state.licence_specialty == 'INDUSTRIELLE'
    selected = await bot.process('Cycle Ingénieur — Génie Industriel — 3 ans', state)
    assert 'Génie Industriel se déroule sur 3 ans' in selected.answer
    assert 'Catalogue officiel' not in selected.answer
    typo = await bot.process('licenece industrielle', state)
    assert 'quelle spécialité précise' in typo.answer
    assert 'Catalogue officiel' not in typo.answer
    llm.generate.assert_not_called()


@pytest.mark.asyncio
async def test_incomplete_licence_request_asks_for_specialty_before_recommending(industrial_bot):
    bot, _ = industrial_bot
    state = ConversationState.new(uuid4())

    result = await bot.process("ena licence w nheb nkamel na9ra andkom", state)

    assert state.active_state.licence_specialty is None
    assert "spécialité de licence" in result.answer
    assert result.recommendation is None


@pytest.mark.asyncio
async def test_confirmed_profile_correction_clears_obsolete_licence_state(audit_bot):
    bot, _ = audit_bot
    state = ConversationState.new(uuid4())
    state.active_state.profile = AcademicProfile.LICENCE_HOLDER
    state.active_state.licence_specialty = 'INDUS'
    state.active_state.recommended_offer = 'LICENCE_INFO'
    await bot.process('ena njaht bac', state)
    answer = await bot.process('bac', state)
    assert state.active_state.profile is AcademicProfile.NEW_BAC
    assert state.active_state.licence_specialty is None
    assert state.active_state.recommended_offer is None
    assert 'section de bac' in answer.answer


@pytest.mark.parametrize('specialty,expected', [
    ('MAINTENANCE_INDUSTRIELLE', True), ('LICENCE_EN_MAINTENANCE_INDUSTRIELLE', True),
    ('LOGISTIQUE_INDUSTRIELLE', True), ('INDUSTRIELLE', False), ('INDUS', False), ('DROIT', False),
])
def test_credential_prefix_normalization_never_invents_equivalence(industrial_bot, specialty, expected):
    bot, _ = industrial_bot
    state = ConversationState.new(uuid4()).active_state
    state.profile = AcademicProfile.LICENCE_HOLDER
    state.licence_specialty = specialty
    result, _ = EligibilityService(bot.catalogue.orientation_rules)._evaluate_rule(bot.catalogue.orientation_rules.items[0], state)
    assert result is expected


@pytest.mark.asyncio
async def test_old_session_without_pending_question_accepts_specialty_correction(industrial_bot):
    bot, _ = industrial_bot
    state = ConversationState.new(uuid4())
    state.active_state.profile = AcademicProfile.LICENCE_HOLDER
    state.active_state.licence_specialty = 'INDUS'
    state.active_state.recommended_offer = 'INGENIEUR_INDUSTRIEL'
    bot.esprit.understand_credential = AsyncMock(return_value='INDUSTRIELLE')
    result = await bot.process("indus c'est industrielle", state)
    assert 'intitulé exact' in result.answer
    assert 'Catalogue officiel' not in result.answer
    assert state.active_state.licence_specialty == 'INDUSTRIELLE'


@pytest.mark.asyncio
async def test_valid_industrial_diploma_with_interest_reaches_real_recommendation(industrial_bot):
    from app.services.recommendation.recommendation_service import RecommendationService
    from app.domain.recommendation.schemas import EligibilityStatus
    bot, _ = industrial_bot
    bot.catalogue.parcours.items.append(SimpleNamespace(id=3, code='INGENIEUR', actif=True))
    bot.catalogue.formations.items[-1].description = 'Industrie et maintenance industrielle'
    bot.eligibility_service = EligibilityService(bot.catalogue.orientation_rules)
    bot.recommendation_service = RecommendationService(bot.catalogue, bot.eligibility_service)
    state = ConversationState.new(uuid4())
    response = await bot.process("j'ai une licence en maintenance industrielle", state)
    assert state.active_state.interests
    assert response.recommendation.primary.formation_code == 'INGENIEUR_INDUSTRIEL'
    assert response.recommendation.primary.specialisation_code is None
    assert response.recommendation.primary.eligibility.status is EligibilityStatus.ELIGIBLE
    assert 'Génie Industriel' in response.answer
