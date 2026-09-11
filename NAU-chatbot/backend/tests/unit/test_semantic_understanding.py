import json
from unittest.mock import AsyncMock

import pytest

from app.services.dialogue.esprit_nlu import EspritNluService, _semantic_cache


@pytest.fixture(autouse=True)
def isolated_cache():
    _semantic_cache.clear()
    yield
    _semantic_cache.clear()


def payload(**updates):
    value = dict(label='IN_SCOPE', confidence=.95, iit_signal=True,
                 normalized='Quels stages ?', intents=['INTERNSHIPS'], social='')
    value.update(updates)
    return json.dumps(value)


@pytest.mark.asyncio
async def test_cache_reuses_interpretation_only_with_same_context():
    provider=AsyncMock()
    provider.generate.return_value=payload()
    service=EspritNluService(provider)
    first=await service.understand('stgg', 'licence informatique')
    assert await service.understand('stgg', 'licence informatique') == first
    provider.generate.assert_awaited_once()
    await service.understand('stgg', 'architecture')
    assert provider.generate.await_count==2


@pytest.mark.parametrize('raw', ['not json', payload(intents=['DELETE_DATABASE']),
    payload(confidence=2), payload(normalized=['invalid']), payload(social='RESET')])
@pytest.mark.asyncio
async def test_invalid_model_output_cannot_become_a_route(raw):
    provider=AsyncMock()
    provider.generate.return_value=raw
    with pytest.raises((ValueError, TypeError)):
        await EspritNluService(provider).understand('unknown')
    assert not _semantic_cache


@pytest.mark.asyncio
async def test_uncertain_interpretations_are_not_cached():
    provider=AsyncMock()
    provider.generate.return_value=payload(label='UNCLEAR', confidence=.3, intents=[])
    await EspritNluService(provider).understand('unknown')
    assert not _semantic_cache


@pytest.mark.asyncio
@pytest.mark.parametrize('message,model_title,expected', [
    ("indus c'est industrielle", 'maintenance industrielle', 'INDUSTRIELLE'),
    ('maintenance industrielle', 'maintenance industrielle', 'MAINTENANCE_INDUSTRIELLE'),
    ('je veux voir les formations', 'maintenance industrielle', None),
])
async def test_credential_model_cannot_add_an_unmentioned_specialty(message, model_title, expected):
    provider = AsyncMock()
    provider.generate.return_value = json.dumps({'specialty': model_title, 'confidence': .95})
    assert await EspritNluService(provider).understand_credential(message) == expected
