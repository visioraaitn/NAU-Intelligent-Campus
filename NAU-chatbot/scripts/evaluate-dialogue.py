#!/usr/bin/env python3
"""Evaluate the real dialogue pipeline against local models and seeded data.

No user accounts or conversation histories are created. Each scenario has an
isolated in-memory state; SQL runs in a read-only transaction. Exit nonzero on
any failed assertion. Run from the repository with backend/.venv/bin/python.
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from sqlalchemy import text
from app.core.config import get_settings
from app.core.dependencies import orchestrator
from app.domain.conversation.models import ConversationState
from app.infrastructure.chroma import AsyncChromaRepository
from app.infrastructure.db.session import close_database, get_session_factory
from app.infrastructure.inference import HttpInferenceClient


class MeasuredInference(HttpInferenceClient):
    calls = 0

    async def generate(self, *args, **kwargs):
        self.calls += 1
        return await super().generate(*args, **kwargs)


async def evaluate(args):
    cases = json.loads(args.cases.read_text())
    provider = MeasuredInference(get_settings())
    chroma = AsyncChromaRepository(get_settings())
    results = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        async with get_session_factory()() as db:
            await db.execute(text('SET TRANSACTION READ ONLY'))
            bot = orchestrator(db, provider, chroma)
            for case in cases:
                if args.scenario and case['name'] not in args.scenario:
                    continue
                state = ConversationState.new(uuid4())
                for turn in case['turns']:
                    started, calls = time.monotonic(), provider.calls
                    result = {'scenario': case['name'], 'message': turn['message']}
                    failures = []
                    try:
                        response = await bot.process(turn['message'], state)
                        state = response.state
                        answer = response.answer
                        result.update(answer=answer, intents=list(response.intents),
                                      profile=state.active_state.profile.value,
                                      specialty=state.active_state.licence_specialty,
                                      subject=state.active_subject.value,
                                      target=state.active_state.recommended_offer)
                        for term in turn.get('contains', []):
                            if term.casefold() not in answer.casefold():
                                failures.append('missing text: ' + term)
                        for term in turn.get('excludes', []):
                            if term.casefold() in answer.casefold():
                                failures.append('unexpected text: ' + term)
                        for intent in turn.get('intents', []):
                            if intent not in response.intents:
                                failures.append('missing intent: ' + intent)
                        for key in ('profile', 'specialty', 'subject', 'target'):
                            if key in turn and result[key] != turn[key]:
                                failures.append(f'{key}: expected {turn[key]}, got {result[key]}')
                        if not answer.strip():
                            failures.append('empty answer')
                    except Exception as error:
                        failures.append(type(error).__name__ + ': ' + str(error))
                    result.update(seconds=round(time.monotonic() - started, 3),
                                  llm_calls=provider.calls - calls, failures=failures)
                    if turn.get('no_llm') and result['llm_calls']:
                        failures.append('unnecessary model call')
                    results.append(result)
                    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2))
                    print(case['name'], turn['message'], result['seconds'],
                          'FAIL ' + '; '.join(failures) if failures else 'PASS', flush=True)
    finally:
        await provider._client.aclose()
        await close_database()
    failed = sum(bool(result['failures']) for result in results)
    print(f'{len(results) - failed}/{len(results)} passed; report: {args.output}')
    return int(bool(failed) or not results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, default=ROOT / 'backend/tests/evals/conversation_quality.json')
    parser.add_argument('--output', type=Path, default=ROOT / '.runtime/audit/dialogue-evaluation.json')
    parser.add_argument('--scenario', action='append')
    raise SystemExit(asyncio.run(evaluate(parser.parse_args())))
