from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from app.domain.conversation.models import AcademicProfile, ConversationState
from app.services.dialogue.contextual_modifier import ContextScope
from app.services.dialogue.dialogue_act_detector import DialogueAct
from app.services.dialogue.intent_detector import IntentDetector
from app.services.dialogue.esprit_nlu import DomainClassification, SemanticUnderstanding
from app.services.dialogue.negation_detector import NegationDetector
from app.services.dialogue.raw_fact_extractor import RawFactExtractor
from app.services.dialogue.profile_resolver import ProfileResolver
from tests.unit.test_conversation_audit import audit_bot


@pytest.mark.parametrize('message', [
    'nheb naraf kol chy al 9raya',
    'mouch bac letter chnouma les parcours fel iit nhb naraf kol chy',
    'je veux tout savoir sur les études',
])
def test_new_topic_does_not_inherit_previous_fees(message):
    result = IntentDetector().detect(message, previous=['FEES'], scope=ContextScope.ALL,
        dialogue_act=DialogueAct.ASK_INFORMATION, slot_parsed=False)
    assert 'FEES' not in result


@pytest.mark.parametrize('message', ['kol chy', 'tout', 'kolhom'])
def test_standalone_expansion_keeps_previous_topic(message):
    result = IntentDetector().detect(message, previous=['FEES'], scope=ContextScope.ALL,
        dialogue_act=DialogueAct.ASK_INFORMATION, slot_parsed=False)
    assert result == ['FEES']


@pytest.mark.asyncio
async def test_catalogue_question_after_fees_uses_current_semantics(audit_bot):
    bot, _ = audit_bot
    bot.esprit.understand = AsyncMock(return_value=SemanticUnderstanding(
        DomainClassification('IN_SCOPE', .95, True), 'Quels sont les parcours à IIT ?', ('CATALOG',)))
    state = ConversationState.new(uuid4())
    state.active_state.last_intents = ['FEES']
    state.active_state.profile = AcademicProfile.NEW_BAC
    state.active_state.bac_specialty = 'LETTERS'
    result = await bot.process('mouch bac letter chnouma les parcours fel iit nhb naraf kol chy', state)
    assert 'CATALOG' in result.intents and 'FEES' not in result.intents
    assert 'formations IIT' in result.answer
    assert state.active_state.bac_specialty is None


def test_denied_bac_is_not_written_back_as_a_positive_fact():
    state = ConversationState.new(uuid4())
    state.active_state.profile = AcademicProfile.NEW_BAC
    state.active_state.bac_specialty = 'LETTERS'
    message = 'mouch bac lettres'
    negation = NegationDetector().detect(message)
    facts = RawFactExtractor().extract(message, active_subject=state.active_subject, negation=negation)
    ProfileResolver().apply(state, facts, negation)
    assert state.active_state.bac_specialty is None


@pytest.mark.asyncio
async def test_programme_then_stage_does_not_repeat_registration_pitch(audit_bot):
    bot, _ = audit_bot
    state = ConversationState.new(uuid4())
    state.turn_count = 10
    first = await bot.process('programme licence informatique', state)
    assert 'pré-inscription' not in first.answer
    second = await bot.process('fiha stage walla ?', state)
    assert 'Stage international' in second.answer
    assert 'pré-inscription' not in second.answer
    assert state.active_state.pending_action is None


@pytest.mark.asyncio
async def test_standalone_scope_bypasses_fallible_domain_model(audit_bot):
    bot, _ = audit_bot
    bot.esprit.understand = AsyncMock(side_effect=AssertionError('Context already resolves this turn'))
    state = ConversationState.new(uuid4())
    state.active_state.last_intents = ['FEES']
    result = await bot.process('kol chy', state)
    assert result.intents == ('FEES',)
    bot.esprit.understand.assert_not_called()
