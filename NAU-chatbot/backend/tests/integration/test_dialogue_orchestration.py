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


class NoRecommendation:
    async def recommend(self, subject):
        del subject
        from app.domain.recommendation.schemas import RecommendationDecision

        return RecommendationDecision(None, None)


def _orchestrator(repository_factory):
    prepa = SimpleNamespace(
        id=10,
        parcours_id=1,
        code="PREPA_GENERAL",
        nom="Cycle Préparatoire",
        description="Prépa MP",
        duree_annees=2,
        intitule_diplome=None,
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


async def test_multiple_factual_questions_are_answered_in_one_turn(
    repository_factory,
) -> None:
    orchestrator, rag = _orchestrator(repository_factory)

    result = await orchestrator.process(
        "quelles formations propose l'IIT, b9adeh et winek ?",
        ConversationState.new(uuid4()),
    )

    assert "formations IIT" in result.answer
    assert "Tarifs publics" in result.answer
    assert "Technopole El Ons" in result.answer
    assert rag.plans == []


async def test_location_question_cannot_fall_through_to_unknown_formation(
    repository_factory,
) -> None:
    orchestrator, rag = _orchestrator(repository_factory)

    result = await orchestrator.process(
        "où est l'IIT à Hay El Ons et Mharza ?",
        ConversationState.new(uuid4()),
    )

    assert "Technopole El Ons" in result.answer
    assert "Route Mharza" in result.answer
    assert "L'IIT n'a pas de centre" not in result.answer
    assert rag.plans == []


async def test_evening_question_does_not_enter_programme_llm_path(
    repository_factory,
) -> None:
    orchestrator, rag = _orchestrator(repository_factory)

    result = await orchestrator.process(
        "najjem na9ra bel lil ?",
        ConversationState.new(uuid4()),
    )

    assert "cours du soir" in result.answer
    assert "administration" in result.answer
    assert rag.plans == []


@pytest.mark.parametrize("message", ["j'ai une licence en droit", "j'ai un bac lettres"])
async def test_external_profile_without_active_rule_contacts_administration(
    repository_factory,
    message,
) -> None:
    orchestrator, rag = _orchestrator(repository_factory)
    orchestrator.recommendation_service = NoRecommendation()

    result = await orchestrator.process(message, ConversationState.new(uuid4()))

    assert "aucune orientation IIT confirmée" in result.answer
    assert "administration IIT" in result.answer
    assert "Licence en Informatique" not in result.answer
    assert rag.plans == []
