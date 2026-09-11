"""Routing regressions; real-model Darija recognition is checked by the live audit."""
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from app.domain.conversation.models import AcademicProfile, ConversationState
from app.services.dialogue.esprit_nlu import DomainClassification, SemanticUnderstanding
from tests.unit.test_conversation_audit import audit_bot


@pytest.mark.asyncio
async def test_semantic_thanks_preserves_pending_action_profile_and_next_question(audit_bot):
    bot, _ = audit_bot
    state = ConversationState.new(uuid4())
    await bot.process('programme licence informatique', state)
    state.active_state.profile = AcademicProfile.NEW_BAC
    state.active_state.pending_action = 'PREINSCRIPTION'
    before = state.active_state.model_dump()
    bot.esprit.understand_social = AsyncMock(return_value=SemanticUnderstanding(
        DomainClassification('SOCIAL', .95), '', (), 'THANKS'))
    result = await bot.process('yeftah alik', state)
    assert result.answer.startswith('Avec plaisir')
    assert state.active_state.model_dump() == before
    assert 'http' not in result.answer
    followup = await bot.process('durée ?', state)
    assert followup.answer.strip() == 'La formation dure 3 ans.'


@pytest.mark.asyncio
async def test_thanks_with_question_retains_every_academic_topic(audit_bot):
    bot, llm = audit_bot
    bot.esprit.understand_social = AsyncMock(side_effect=AssertionError('Academic question'))
    result = await bot.process(
        'aychek, programme et stages licence informatique ?', ConversationState.new(uuid4()))
    assert 'Programmation' in result.answer
    assert 'Stage international' in result.answer
    bot.esprit.understand_social.assert_not_called()
    llm.generate.assert_not_called()


@pytest.mark.asyncio
async def test_thanks_does_not_bypass_moderation(audit_bot):
    bot, llm = audit_bot
    state = ConversationState.new(uuid4())
    before = state.model_dump()
    result = await bot.process('aychek fok ala ezzebi', state)
    assert 'respectueux' in result.answer
    assert state.model_dump() == before
    llm.generate.assert_not_called()
