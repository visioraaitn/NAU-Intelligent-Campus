from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.conversation.models import ConversationState
from tests.unit.test_conversation_audit import audit_bot


@pytest.mark.asyncio
async def test_followups_start_with_requested_fact_without_repeated_identity(audit_bot):
    bot, llm = audit_bot
    state = ConversationState.new(uuid4())
    programme = await bot.process('programme licence informatique', state)
    assert programme.answer.startswith('Tu étudieras')
    assert 'Programmation' in programme.answer
    assert programme.answer.index('https://') > programme.answer.index('Programmation')
    stages = await bot.process('fiha stage walla ?', state)
    assert stages.answer.startswith('Pour les stages')
    assert 'Stage international' in stages.answer
    projects = await bot.process('les projets', state)
    assert 'Projet Tutoré' in projects.answer
    assert stages.answer.splitlines()[-1] != projects.answer.splitlines()[-1]
    certificates = await bot.process('certifications', state)
    assert certificates.answer.startswith('Les certifications')
    assert 'ISTQB' in certificates.answer
    assert "n'est pas automatique" in certificates.answer
    duration = await bot.process('durée ?', state)
    assert duration.answer.strip() == 'La formation dure 3 ans.'
    for result in (stages, certificates, duration):
        assert 'https://' not in result.answer
        assert 'Diplôme préparé' not in result.answer
        assert 'pré-inscription' not in result.answer
    llm.generate.assert_not_called()


@pytest.mark.asyncio
async def test_new_formation_gets_its_own_source_and_facts(audit_bot):
    bot, _ = audit_bot
    bot.catalogue.formations.items.append(SimpleNamespace(
        id=30, parcours_id=4, code='ARCHITECTURE_DNA', nom="Diplôme National d'Architecte",
        intitule_diplome="Diplôme National d'Architecte", duree_annees=6, actif=True))
    state = ConversationState.new(uuid4())
    await bot.process('durée licence informatique', state)
    result = await bot.process('durée architecture', state)
    assert '6 ans' in result.answer
    assert 'architecture-2' in result.answer
    assert '3 ans' not in result.answer


@pytest.mark.asyncio
async def test_multi_topic_answer_preserves_all_topics_without_repeated_evidence(audit_bot):
    bot, _ = audit_bot
    result = await bot.process('licence informatique : programme, certifications, pratique, projets et stages ?', ConversationState.new(uuid4()))
    for fact in ['Programmation', 'ISTQB', 'Projet Tutoré', 'Stage international']:
        assert fact in result.answer
    assert result.answer.count('Projet Tutoré') == 1
    assert result.answer.count("modalités exactes") == 1
    assert result.answer.count('https://') == 1


@pytest.mark.asyncio
async def test_specialisation_list_is_not_repeated_on_programme_followup(audit_bot):
    bot, _ = audit_bot
    bot.catalogue.specialisations.items.append(SimpleNamespace(id=201, formation_id=20,
        code='LIC_INFO_GLSI', nom='Génie Logiciel', description=None, actif=True))
    state = ConversationState.new(uuid4())
    first = await bot.process('programme licence informatique', state)
    assert 'Génie Logiciel' in first.answer
    second = await bot.process('donne tous les modules', state)
    assert 'Programmation' in second.answer
    assert 'Génie Logiciel' not in second.answer
    assert 'Laquelle' not in second.answer


@pytest.mark.asyncio
async def test_explicit_source_request_keeps_link_accessible(audit_bot):
    bot, _ = audit_bot
    state = ConversationState.new(uuid4())
    await bot.process('programme licence informatique', state)
    result = await bot.process('programme et lien officiel', state)
    assert 'https://iit.tn/licences/' in result.answer
    assert 'Programmation' in result.answer
