from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from app.domain.conversation.models import ConversationState
from app.services.dialogue.turn_gate import TurnGate, TurnType
from app.services.dialogue.esprit_nlu import DomainClassification, SemanticUnderstanding
from tests.unit.test_conversation_audit import audit_bot


@pytest.mark.parametrize('message', [
    'bellehi fok ala ezzebi', 'ti fok al aezzebi', 'fok ala ezzebiiii',
    'FOK ALA EZZEBI', 'fok ala ezzebi w les tarifs', 'فك علي زبي',
    'bellehi barra nayek', 'zab alik chnou hedha', 'niiiik',
    'ezzebi', 'fok ala ezzebi', 'barra neyk', 'barra neyek',
    'barra neykkk', 'barra neyk w les tarifs', 'e.z.z.e.b.i',
    'e z z e b i', 'ezz**ebi', 'ne\u200byk', 'n.e.y.k',
    'ｂａｒｒａ ｎｅｙｋ', 'fok ala ezz3bi', 'بَرَّا نِيك',
    'ba3bousa',
])
def test_abusive_spelling_variants_are_blocked_before_academic_routing(message):
    assert TurnGate().classify(message) is TurnType.INAPPROPRIATE


@pytest.mark.parametrize('message', ['7asba les frais', 'Kasba', 'kahraba',
    'Nabeul', 'les stages', 'mrigel', 'aychou', 'yehik', 'cvnn', 'les tarifs',
    'aychek', 'ybereklek', 'yeftah alik', 'ya3tik sa7a', 'projet New York',
    'nylon', 'noyau', 'analyse', 'e-learning', 's t a g e'])
def test_benign_words_are_not_fuzzy_blocked(message):
    assert TurnGate().classify(message) is not TurnType.INAPPROPRIATE


@pytest.mark.asyncio
async def test_semantic_moderation_preserves_profile_and_history(audit_bot):
    bot, _ = audit_bot
    bot.esprit.understand = AsyncMock(return_value=SemanticUnderstanding(
        DomainClassification('INAPPROPRIATE', .98), ''))
    state = ConversationState.new(uuid4())
    before = state.model_dump()
    result = await bot.process('enti ma teswa chay', state)
    assert 'respectueux' in result.answer
    assert result.state is state and state.model_dump() == before


@pytest.mark.asyncio
async def test_social_agreement_does_not_create_academic_intents(audit_bot):
    bot, _ = audit_bot
    bot.esprit.understand_social = AsyncMock(return_value=SemanticUnderstanding(
        DomainClassification('SOCIAL', .97), '', (), 'ACKNOWLEDGEMENT'))
    bot.esprit.understand = AsyncMock(side_effect=AssertionError('Already resolved'))
    state = ConversationState.new(uuid4())
    state.active_state.recommended_offer = 'LICENCE_INFO'
    result = await bot.process('mriigelll', state)
    assert "D'accord" in result.answer
    assert state.active_state.pending_action is None
    bot.esprit.understand.assert_not_called()


@pytest.mark.parametrize('message', ['barra neyk', 'e.z.z.e.b.i', 'barra neyk w les tarifs'])
@pytest.mark.asyncio
async def test_obfuscated_insults_block_even_when_model_is_unavailable(audit_bot, message):
    bot, llm = audit_bot
    llm.generate.side_effect = RuntimeError('Model unavailable')
    state = ConversationState.new(uuid4())
    state.active_state.recommended_offer = 'LICENCE_INFO'
    state.active_state.pending_action = 'PREINSCRIPTION'
    before = state.model_dump()
    result = await bot.process(message, state)
    assert 'respectueux' in result.answer
    assert state.model_dump() == before
    llm.generate.assert_not_called()
