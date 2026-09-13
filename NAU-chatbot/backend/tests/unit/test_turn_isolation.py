"""Routing regressions: unseen content, topic permissions and evidence boundaries."""
import json
from dataclasses import replace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.conversation.models import AcademicProfile, ConversationState
from app.domain.rag.schemas import RagFact, RagResult
from app.services.academic.target_resolver import AcademicTargetResolver
from app.services.dialogue.esprit_nlu import DomainClassification, SemanticUnderstanding
from app.services.dialogue.guards.factual import FactualGuard
from app.services.dialogue.intent_detector import IntentDetector
from app.services.dialogue.contextual_modifier import ContextScope
from app.services.dialogue.dialogue_act_detector import DialogueAct
from app.services.rag.query_planner import RagQueryPlanner
from tests.unit.test_conversation_audit import audit_bot


def meaning(intents=(), label='IN_SCOPE', normalized='', uses_context=False):
    return SemanticUnderstanding(DomainClassification(label, .96, label == 'IN_SCOPE'), normalized, tuple(intents), uses_context=uses_context)


@pytest.mark.asyncio
@pytest.mark.parametrize('message', [
    'Quel est le prix du billet de train pour Gabès ?',
    'Où se trouve le meilleur restaurant de la ville ?',
    'Donne le programme des élections municipales',
    'Peux-tu expliquer le marché des voitures anciennes ?',
])
async def test_generic_intent_keywords_do_not_bypass_domain(audit_bot, message):
    bot, _ = audit_bot
    state = ConversationState.new(uuid4())
    await bot.process('programme licence informatique', state)
    state.active_state.profile = AcademicProfile.NEW_BAC
    state.active_state.bac_specialty = 'MATH'
    bot.esprit.understand = AsyncMock(return_value=meaning(label='OUT_OF_SCOPE'))
    result = await bot.process(message, state)
    assert result.intents == ('OUT_OF_SCOPE',)
    assert bot.esprit.understand.call_args.args[1] == ''
    assert not state.active_state.topic_open
    assert state.active_state.profile == AcademicProfile.NEW_BAC


@pytest.mark.asyncio
async def test_complete_new_question_does_not_reuse_target_or_intent(audit_bot):
    bot, _ = audit_bot
    state = ConversationState.new(uuid4())
    await bot.process('programme licence informatique', state)
    bot.esprit.understand = AsyncMock(return_value=meaning(['FEES']))
    result = await bot.process("Quel budget faut-il prévoir pour étudier chez vous ?", state)
    assert result.intents == ('FEES',)
    assert state.active_state.current_offer is None
    assert state.active_state.recommended_offer == 'LICENCE_INFO'
    assert state.active_state.last_intents == ['FEES']
    assert bot.esprit.understand.call_args.args[1] == ''
    # A clarification cannot resurrect the historical offer on the next turn.
    await bot.process('et les matières ?', state)
    assert state.active_state.current_offer is None


@pytest.mark.asyncio
async def test_short_followup_reuses_target_but_replaces_intent(audit_bot):
    bot, _ = audit_bot
    state = ConversationState.new(uuid4())
    await bot.process('programme licence informatique', state)
    result = await bot.process('et les frais ?', state)
    assert result.intents == ('FEES',)
    assert state.active_state.current_offer == 'LICENCE_INFO'
    assert 'Programmation' not in result.answer


@pytest.mark.asyncio
async def test_external_turn_closes_topic_but_preserves_profile(audit_bot):
    bot, _ = audit_bot
    state = ConversationState.new(uuid4())
    state.active_state.profile = AcademicProfile.NEW_BAC
    await bot.process('programme licence informatique', state)
    await bot.process('la météo demain ?', state)
    result = await bot.process('et les frais ?', state)
    assert result.intents == ('FEES',)
    assert state.active_state.current_offer is None
    assert state.active_state.profile == AcademicProfile.NEW_BAC


@pytest.mark.asyncio
async def test_pending_credential_does_not_consume_information_question(audit_bot):
    bot, _ = audit_bot
    state = ConversationState.new(uuid4())
    subject = state.active_state
    subject.profile = AcademicProfile.LICENCE_HOLDER
    subject.pending_slot = 'LICENCE_SPECIALTY'
    subject.last_intents = ['ORIENTATION']
    result = await bot.process('Quels sont les frais en licence informatique ?', state)
    assert result.intents == ('FEES',)
    assert subject.licence_specialty is None
    assert subject.pending_slot == 'LICENCE_SPECIALTY'
    assert subject.interests == []


@pytest.mark.asyncio
@pytest.mark.parametrize('message', ['شنية نقرا في الاختصاص هذا', 'chnyet l7ajet elli net3almhom ba3d ?', 'Que découvre-t-on durant les ateliers de cette formation ?'])
async def test_unseen_semantic_formulations_use_validated_intents(audit_bot, message):
    bot, _ = audit_bot
    state = ConversationState.new(uuid4())
    await bot.process('programme licence informatique', state)
    bot.esprit.understand = AsyncMock(return_value=meaning(['PROGRAMME'], uses_context=True))
    result = await bot.process(message, state)
    assert 'PROGRAMME' in result.intents
    assert 'Programmation' in result.answer


@pytest.mark.asyncio
async def test_model_completes_unrecognized_second_axis(audit_bot):
    bot, _ = audit_bot
    bot.esprit.understand = AsyncMock(return_value=meaning(['FEES', 'PROGRAMME']))
    result = await bot.process('frais licence informatique et ce que nous allons apprendre concrètement ?', ConversationState.new(uuid4()))
    assert set(result.intents) == {'FEES', 'PROGRAMME'}
    assert 'Programmation' in result.answer
    bot.esprit.understand.assert_awaited_once()


@pytest.mark.parametrize('message,expected', [
    ('geniee infoo', 'INFO'), ('henie info', 'INFO'), ('genie idus', 'IND'),
])
def test_fuzzy_compares_entities_not_sibling_aliases(message, expected):
    aliases = {'genie info': 'INFO', 'genie inf': 'INFO', 'genie indus': 'IND', 'genie industriel': 'IND'}
    assert AcademicTargetResolver._fuzzy_alias_code(message, aliases) == expected


def test_fuzzy_tie_between_different_offers_requires_clarification():
    assert AcademicTargetResolver._fuzzy_alias_code('geni', {'genie': 'A', 'genia': 'B'}) is None


def test_more_inside_complete_question_does_not_inherit_fees():
    intents = IntentDetector().detect('Je voudrais plus de renseignements sur les études', previous=['FEES'], scope=ContextScope.MORE, dialogue_act=DialogueAct.ASK_INFORMATION, slot_parsed=False)
    assert 'FEES' not in intents


def test_multi_intent_rag_plans_keep_distinct_filters():
    plans = RagQueryPlanner().plans('programme et frais', ['FEES', 'PROGRAMME'], formation_code='LICENCE_INFO', specialisation_code=None)
    assert {plan.entity_type for plan in plans} == {'TARIF', 'FORMATION_ELEMENT'}
    assert all(plan.formation_code == 'LICENCE_INFO' for plan in plans)


def fact(text='Information académique : une rampe est documentée.'):
    return RagFact(text, 'FORMATION_ELEMENT', 1, None, None, 'SRC_ACCESS', 'element:1', 'INFORMATION')


@pytest.mark.parametrize('raw', [
    'Les frais sont de 9500 TND et on étudie la médecine.',
    '{"fact_ids": [0], "answer": "admission garantie"}',
    '{"fact_ids": [12]}', '{"fact_ids": [-1]}', '{"fact_ids": [true]}',
    '{"fact_ids": [0, 0]}', '[]',
])
def test_final_generation_cannot_introduce_new_claims(raw):
    with pytest.raises((ValueError, TypeError)):
        FactualGuard.render_selection(raw, [fact('Tarif : 800 TND. Durée : 3 ans.')])


def test_final_selection_renders_exact_sourced_values():
    evidence = fact('Tarif annuel : 800 TND. Durée : 3 ans.')
    assert FactualGuard.render_selection('{"fact_ids": [0]}', [evidence]) == evidence.text
    with pytest.raises(ValueError):
        FactualGuard.render_selection('{"fact_ids": [0]}', [replace(evidence, source_ref=None)])


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['rag', 'empty', 'llm', 'invented', 'unsourced'])
async def test_rag_or_model_failure_never_invents(audit_bot, failure, caplog):
    bot, llm = audit_bot
    bot.esprit.understand = AsyncMock(return_value=meaning(['ACADEMIC_INFO']))
    async def retrieve(plan):
        if failure == 'rag':
            raise RuntimeError('service unavailable')
        return RagResult(plan, facts=() if failure == 'empty' else (replace(fact(), source_ref=None) if failure == 'unsourced' else fact(),))
    bot.rag.retrieve.side_effect = retrieve
    if failure == 'llm':
        llm.generate.side_effect = RuntimeError('inference unavailable')
    else:
        llm.generate.return_value = 'Le parking coûte 900 TND, et tous sont admis.'
    result = await bot.process('Est-ce que vos locaux accueillent les fauteuils roulants ?', ConversationState.new(uuid4()))
    assert '900' not in result.answer and 'admis' not in result.answer
    assert result.intents == ('ACADEMIC_INFO',)
    if failure in {'rag', 'empty', 'unsourced'}:
        llm.generate.assert_not_called()
    if failure in {'rag', 'llm', 'invented'}:
        assert 'unavailable' in caplog.text


@pytest.mark.asyncio
async def test_rag_final_gets_current_question_without_profile_history(audit_bot):
    bot, llm = audit_bot
    bot.esprit.understand = AsyncMock(return_value=meaning(['ACADEMIC_INFO']))
    bot.rag.retrieve.side_effect = lambda plan: RagResult(plan, facts=(fact(),))
    llm.generate.return_value = '{"fact_ids": [0]}'
    state = ConversationState.new(uuid4())
    state.active_state.profile = AcademicProfile.LICENCE_HOLDER
    state.active_state.licence_specialty = 'MECANIQUE'
    state.active_state.recommended_offer = 'LICENCE_INFO'
    result = await bot.process('Est-ce que vos locaux accueillent les fauteuils roulants ?', state)
    assert 'rampe' in result.answer
    final_prompt = llm.generate.call_args.args[1][1].content
    assert 'MECANIQUE' not in final_prompt and 'LICENCE_INFO' not in final_prompt


@pytest.mark.asyncio
async def test_semantic_paraphrase_cannot_invent_missing_formation(audit_bot):
    bot, _ = audit_bot
    bot.esprit.understand = AsyncMock(return_value=meaning(['PROGRAMME'], normalized='programme licence informatique'))
    result = await bot.process('stg w prjts', ConversationState.new(uuid4()))
    assert 'Programmation' not in result.answer
    assert result.state.active_state.current_offer is None
