from uuid import uuid4

import pytest

from app.domain.conversation.models import AcademicProfile, ConversationState
from app.domain.recommendation.schemas import EligibilityStatus
from app.services.dialogue.negation_detector import NegationDetector
from app.services.dialogue.normalizer import normalize_degree_spelling
from app.services.dialogue.raw_fact_extractor import RawFactExtractor
from tests.unit.test_aaa_conversation import industrial_bot
from tests.unit.test_conversation_audit import audit_bot


@pytest.mark.parametrize('separator', [', est-ce que je peux intégrer', ' puis-je intégrer', '; puis-je intégrer'])
def test_following_question_is_not_part_of_owned_diploma(separator):
    message = "j'ai une licence en maintenance industrielle" + separator + ' le génie industriel et quels sont les frais ?'
    facts = RawFactExtractor().extract(message, active_subject=ConversationState.new(uuid4()).active_subject,
                                       negation=NegationDetector().detect(message))
    assert facts.licence_specialty == 'MAINTENANCE_INDUSTRIELLE'


def test_license_spelling_is_normalized_without_changing_the_degree_meaning():
    assert normalize_degree_spelling("license indus") == "licence indus"


@pytest.mark.asyncio
async def test_engineering_goal_does_not_erase_programme_and_fees(industrial_bot):
    bot, _ = industrial_bot
    result = await bot.process('je veux devenir ingénieur, programme et frais du génie industriel ?', ConversationState.new(uuid4()))
    assert {'PROGRAMME', 'FEES'} <= set(result.intents)
    assert 'tarif' in result.answer.casefold()


@pytest.mark.asyncio
async def test_ineligible_profile_still_receives_requested_admission_information(industrial_bot):
    bot, _ = industrial_bot
    from app.services.eligibility.eligibility_service import EligibilityService

    bot.eligibility_service = EligibilityService(bot.catalogue.orientation_rules)
    state = ConversationState.new(uuid4())
    state.active_state.profile = AcademicProfile.LICENCE_HOLDER
    state.active_state.licence_specialty = "DROIT"

    result = await bot.process("admission génie industriel", state)

    assert "Admission" in result.answer
    assert "Remarque :" in result.answer
    assert "ne bloque pas ta demande" in result.answer


@pytest.mark.asyncio
async def test_looking_at_another_licence_does_not_change_owned_diploma(audit_bot):
    bot, _ = audit_bot
    state = ConversationState.new(uuid4())
    state.active_state.profile = AcademicProfile.LICENCE_HOLDER
    state.active_state.licence_specialty = 'MAINTENANCE_INDUSTRIELLE'
    response = await bot.process('programme licence informatique', state)
    assert 'Programmation' in response.answer
    assert state.active_state.licence_specialty == 'MAINTENANCE_INDUSTRIELLE'


@pytest.mark.asyncio
async def test_bac_pricing_question_is_not_a_profile_correction(audit_bot):
    bot, _ = audit_bot
    state = ConversationState.new(uuid4())
    state.active_state.profile = AcademicProfile.LICENCE_HOLDER
    response = await bot.process('tarifs pour un bac math ?', state)
    assert 'FEES' in response.intents
    assert state.active_state.profile is AcademicProfile.LICENCE_HOLDER
    assert state.active_state.pending_slot != 'PROFILE_CONFIRMATION'


@pytest.mark.asyncio
async def test_unfinished_diploma_produces_conditional_recommendation(industrial_bot):
    from types import SimpleNamespace
    from app.services.eligibility.eligibility_service import EligibilityService
    from app.services.recommendation.recommendation_service import RecommendationService
    bot, llm = industrial_bot
    bot.catalogue.parcours.items.append(SimpleNamespace(id=3, code='INGENIEUR', actif=True))
    bot.catalogue.formations.items[-1].description = 'Industrie et maintenance industrielle'
    bot.eligibility_service = EligibilityService(bot.catalogue.orientation_rules)
    bot.recommendation_service = RecommendationService(bot.catalogue, bot.eligibility_service)
    result = await bot.process('je suis en licence maintenance industrielle', ConversationState.new(uuid4()))
    assert result.recommendation.primary.eligibility.status is EligibilityStatus.UNKNOWN
    assert 'doit être validé' in result.answer
    assert 'piste à examiner' in result.answer
    llm.generate.assert_not_called()
