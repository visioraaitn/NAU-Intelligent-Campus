from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.conversation.models import ConversationState
from app.domain.rag.schemas import RagResult
from app.domain.recommendation.schemas import EligibilityDecision, EligibilityStatus
from app.services.dialogue.orchestrator import ChatOrchestrator


pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class CapturingRag:
    def __init__(self) -> None:
        self.plans = []

    async def retrieve(self, plan):
        self.plans.append(plan)
        return RagResult(plan=plan)


class StableLlm:
    async def generate(self, role, messages, *, max_new_tokens):
        del messages, max_new_tokens
        if role == "esprit":
            return ""
        return "Les tarifs actifs sont présentés à titre indicatif selon les informations publiées."


class UnknownEligibility:
    async def evaluate(self, subject, formation, specialisation=None):
        del subject
        return EligibilityDecision(
            EligibilityStatus.UNKNOWN,
            formation.id,
            formation.code,
            specialisation.id if specialisation else None,
            specialisation.code if specialisation else None,
            unknown_reasons=("Informations complémentaires nécessaires.",),
        )


class UnusedRecommendation:
    async def recommend(self, subject):  # pragma: no cover - a FEES turn must not call this
        del subject
        raise AssertionError("a factual fees request must not trigger recommendation")


def _orchestrator(repository_factory):
    prepa = SimpleNamespace(
        id=10,
        parcours_id=1,
        code="PREPA_GENERAL",
        nom="Cycle Préparatoire",
        description="Prépa MP",
        actif=True,
    )
    catalogue = SimpleNamespace(
        parcours=repository_factory(
            [SimpleNamespace(id=1, code="PREPA", nom="Cycle Préparatoire", actif=True)]
        ),
        formations=repository_factory([prepa]),
        specialisations=repository_factory([]),
        tarifs=repository_factory(
            [
                SimpleNamespace(
                    id=20,
                    formation_id=10,
                    specialisation_id=None,
                    frais_inscription=800,
                    mensualite=556,
                    nb_mensualites=9,
                    devise="TND",
                    actif=True,
                )
            ]
        ),
        elements=repository_factory([]),
    )
    rag = CapturingRag()
    return (
        ChatOrchestrator(
            catalogue=catalogue,
            eligibility=UnknownEligibility(),
            recommendation=UnusedRecommendation(),
            rag=rag,
            llm=StableLlm(),
        ),
        rag,
    )


async def test_all_fees_are_rendered_directly_from_structured_tariff_data(
    repository_factory,
) -> None:
    orchestrator, rag = _orchestrator(repository_factory)

    result = await orchestrator.process(
        "donne-moi tous les frais",
        ConversationState.new(uuid4()),
    )

    assert result.intents == ("FEES",)
    assert "Cycle Préparatoire" in result.answer
    assert "556 TND" in result.answer
    assert "5 804 TND" in result.answer
    assert rag.plans == []


async def test_current_formation_fees_are_scoped_to_the_named_formation(
    repository_factory,
) -> None:
    orchestrator, rag = _orchestrator(repository_factory)

    result = await orchestrator.process(
        "quel est le prix de la prépa ?",
        ConversationState.new(uuid4()),
    )

    assert "Cycle Préparatoire" in result.answer
    assert "556 TND" in result.answer
    assert rag.plans == []
