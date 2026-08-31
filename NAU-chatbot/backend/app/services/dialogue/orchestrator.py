from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.domain.conversation.models import (
    AcademicProfile,
    ChatMessage,
    ConversationState,
    ConversionStage,
    SubjectState,
)
from app.domain.recommendation.schemas import (
    EligibilityDecision,
    EligibilityStatus,
    RecommendationDecision,
)
from app.services.academic.catalog_service import AcademicCatalogService
from app.services.academic.target_resolver import AcademicTarget, AcademicTargetResolver
from app.services.dialogue.contextual_modifier import ContextScope
from app.services.dialogue.conversion_cta import ConversionCTA
from app.services.dialogue.debug_log import log_stage, readable_summary
from app.services.dialogue.dialogue_act_detector import DialogueAct, DialogueActDetector
from app.services.dialogue.esprit_nlu import EspritNluService
from app.services.dialogue.fallback_response import FallbackResponseBuilder
from app.services.dialogue.guards import AntiRepetitionGuard, FactualGuard, ResponseLengthGuard
from app.services.dialogue.intent_detector import IntentDetector
from app.services.dialogue.human_labels import value_label
from app.services.dialogue.known_facts_builder import KnownFactsBuilder
from app.services.dialogue.negation_detector import NegationDetector
from app.services.dialogue.pending_slot_resolver import PendingSlotResolver
from app.services.dialogue.profile_resolver import ProfileResolver
from app.services.dialogue.prompt_composer import PromptComposer
from app.services.dialogue.qualification_policy import QualificationPolicy
from app.services.dialogue.raw_fact_extractor import RawFactExtractor
from app.services.dialogue.response_policy import focus_topics, response_mode
from app.services.dialogue.structured_response import StructuredResponseBuilder
from app.services.dialogue.turn_gate import TurnGate, TurnType
from app.services.eligibility import EligibilityService
from app.services.llm.providers import LLMProvider
from app.services.rag.query_planner import RagQueryPlanner
from app.services.rag.retriever import RagRetriever
from app.services.recommendation import RecommendationService


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DialogueResponse:
    answer: str
    state: ConversationState
    intents: tuple[str, ...] = ()
    eligibility: EligibilityDecision | None = None
    recommendation: RecommendationDecision | None = None


class ChatOrchestrator:
    def __init__(
        self,
        *,
        catalogue: AcademicCatalogService,
        eligibility: EligibilityService,
        recommendation: RecommendationService,
        rag: RagRetriever,
        llm: LLMProvider,
    ) -> None:
        self.catalogue = catalogue
        self.eligibility_service = eligibility
        self.recommendation_service = recommendation
        self.rag = rag
        self.llm = llm
        self.target_resolver = AcademicTargetResolver(catalogue)
        self.turn_gate = TurnGate()
        self.negations = NegationDetector()
        self.raw_facts = RawFactExtractor()
        self.profile_resolver = ProfileResolver()
        self.pending_slots = PendingSlotResolver()
        self.esprit = EspritNluService(llm)
        self.dialogue_acts = DialogueActDetector()
        self.intents = IntentDetector()
        self.qualification = QualificationPolicy()
        self.query_planner = RagQueryPlanner()
        self.known_facts = KnownFactsBuilder()
        self.prompt = PromptComposer()
        self.fallback = FallbackResponseBuilder()
        self.factual_guard = FactualGuard()
        self.repetition_guard = AntiRepetitionGuard()
        self.length_guard = ResponseLengthGuard()
        self.cta = ConversionCTA()
        self.structured = StructuredResponseBuilder(catalogue)

    async def process(self, message: str, state: ConversationState) -> DialogueResponse:
        first_reply = not any(item.role == "assistant" for item in state.history)
        turn_type = self.turn_gate.classify(message)
        session_id = str(state.session_id)
        log_stage("TURN_GATE", session_id=session_id, turn_type=turn_type.value)

        if turn_type is TurnType.RESET:
            reset = ConversationState.new(state.session_id)
            return self._fixed(message, reset, turn_type, first_reply)
        if turn_type in {TurnType.SECURITY, TurnType.INAPPROPRIATE, TurnType.EMPTY}:
            # Refusal gates do not mutate academic or conversational profile memory.
            return DialogueResponse(self.turn_gate.response(turn_type, first_reply=first_reply), state)
        if turn_type is not TurnType.ACADEMIC:
            return self._fixed(message, state, turn_type, first_reply)

        state.turn_count += 1
        state.started = True
        negation = self.negations.detect(message)
        facts = self.raw_facts.extract(
            message,
            active_subject=state.active_subject,
            negation=negation,
        )
        self.profile_resolver.apply(state, facts, negation)
        subject = state.active_state
        if negation.request_alternative:
            rejected_current = (
                subject.recommended_specialisation or subject.recommended_offer
            )
            if rejected_current:
                subject.rejected_offers = list(
                    dict.fromkeys((*subject.rejected_offers, rejected_current))
                )
        log_stage(
            "RAW_FACTS",
            session_id=session_id,
            subject=facts.subject.value,
            profile=facts.profile.value if facts.profile else None,
            bac=facts.bac_specialty,
        )

        pending = self.pending_slots.resolve(message, subject)
        try:
            esprit_result = await self.esprit.interpret(message)
        except Exception:
            logger.warning("ESPRIT_RESULT unavailable", exc_info=True)
            esprit_result = ""
        log_stage("ESPRIT_RESULT", session_id=session_id, available=bool(esprit_result))

        act = self.dialogue_acts.detect(
            message,
            auxiliary_interpretation=esprit_result,
            scope=facts.scope,
            negation=negation,
            pending_parsed=pending.parsed,
        )
        intents = self.intents.detect(
            message,
            auxiliary_interpretation=esprit_result,
            previous=pending.previous_intents or tuple(subject.last_intents),
            scope=facts.scope,
            dialogue_act=act,
            slot_parsed=pending.parsed,
        )
        if facts.profile and intents == ["GENERAL"]:
            intents = ["ORIENTATION"]
        if facts.target and intents == ["GENERAL"]:
            intents = ["ORIENTATION"]
        log_stage("INTENTS", session_id=session_id, dialogue_act=act.value, intents=intents)

        if "INFORMATIQUE" in subject.rejected_domains and "ORIENTATION" in intents:
            answer = "D'accord, je n'insiste pas sur l'informatique. Je peux uniquement te proposer une autre formation présente dans le catalogue académique actif, sans en inventer. Quel domaine t'intéresse ?"
            return self._finish(state, message, answer, intents, act, first_reply)

        target = await self.target_resolver.resolve(message)
        if (
            "ORIENTATION" in intents
            and subject.target == "ENGINEERING"
            and target is not None
            and target.formation.code.startswith("LICENCE_")
        ):
            target = None
        if target is not None and intents == ["GENERAL"]:
            intents = ["DETAILS"]
        needs_eligibility = bool(
            {"ADMISSION", "ORIENTATION", "PREINSCRIPTION"}.intersection(intents)
        )
        eligibility: EligibilityDecision | None = None
        if target is not None and needs_eligibility:
            eligibility = await self.eligibility_service.evaluate(
                subject,
                target.formation,
                target.specialisation,
            )
            log_stage(
                "ELIGIBILITY",
                session_id=session_id,
                status=eligibility.status.value,
                formation=eligibility.formation_code,
            )
            if eligibility.status is EligibilityStatus.NOT_ELIGIBLE:
                alternative = (
                    await self.recommendation_service.recommend(subject)
                    if "ORIENTATION" in intents or "ADMISSION" in intents
                    else None
                )
                answer = self.fallback.build(intents, (), alternative, eligibility)
                subject.last_intents = intents
                subject.last_scope = facts.scope.value
                subject.last_dialogue_act = act.value
                subject.last_user_message = message
                subject.last_answer_focus = focus_topics(intents)
                subject.covered_topics = list(
                    dict.fromkeys(
                        (*subject.covered_topics, *subject.last_answer_focus)
                    )
                )
                result = self._finish(
                    state,
                    message,
                    answer,
                    intents,
                    act,
                    first_reply,
                    eligibility=eligibility,
                )
                subject.last_answer_text = result.answer
                return result

        slot = self.qualification.choose(subject, intents)
        if slot and subject.asked_slots.get(slot, 0) == 0:
            question = self.qualification.ask(slot, subject, state.turn_count)
            subject.last_intents = intents
            subject.last_dialogue_act = act.value
            subject.last_user_message = message
            subject.conversion_stage = ConversionStage.QUALIFICATION
            return self._finish(state, message, question, intents, act, first_reply)

        recommendation: RecommendationDecision | None = None
        if "ORIENTATION" in intents or "PREINSCRIPTION" in intents:
            recommendation = await self.recommendation_service.recommend(subject)
            log_stage(
                "RECOMMENDATION",
                session_id=session_id,
                primary=(recommendation.primary.formation_code if recommendation.primary else None),
                specialisation=(recommendation.primary.specialisation_code if recommendation.primary else None),
            )
            if target is None and recommendation.primary:
                target = await self._target_from_recommendation(recommendation)
        elif target is None and subject.recommended_offer:
            target = await self._remembered_target(subject.recommended_offer, subject.recommended_specialisation)

        structured_answer: str | None = None
        if "CATALOG" in intents:
            structured_answer = await self.structured.catalogue_overview(message)
        elif "FEES" in intents:
            structured_answer = await self.structured.fees(target)
        elif "ORIENTATION" in intents and recommendation is not None:
            structured_answer = await self.structured.orientation(subject, recommendation)
        elif "PREINSCRIPTION" in intents and target is not None:
            structured_answer = await self.structured.pre_registration(target)
        elif target is not None and {
            "DETAILS",
            "PROGRAMME",
            "CAREERS",
            "MARKET",
            "CERTIFICATIONS",
            "INTERNATIONAL",
            "DURATION",
            "DIFFICULTY",
        }.intersection(intents):
            same_target = (
                target.formation.code == subject.recommended_offer
                and (
                    target.specialisation.code if target.specialisation else None
                )
                == subject.recommended_specialisation
            )
            if (
                "DETAILS" in intents
                and "DETAILS" in subject.last_intents
                and same_target
            ):
                structured_answer = await self.structured.next_detail_step(target)
            else:
                structured_answer = await self.structured.formation_details(target, intents)

        if structured_answer:
            answer = structured_answer
            if recommendation and recommendation.primary:
                subject.recommended_offer = recommendation.primary.formation_code
                subject.recommended_specialisation = recommendation.primary.specialisation_code
                if (
                    "PREINSCRIPTION" not in intents
                    and self.cta.should_add(state, subject, intents, act, recommendation)
                ):
                    answer = self.cta.add(answer, subject, state.turn_count)
                subject.offer_intro_done = True
                subject.last_recommendation_turn = state.turn_count
                subject.conversion_stage = ConversionStage.RECOMMENDATION
                if "PREINSCRIPTION" in intents:
                    subject.conversion_stage = ConversionStage.PRE_REGISTRATION
            elif target is not None and {
                "DETAILS",
                "PROGRAMME",
                "CAREERS",
                "MARKET",
                "CERTIFICATIONS",
                "INTERNATIONAL",
                "DURATION",
                "DIFFICULTY",
            }.intersection(intents):
                subject.recommended_offer = target.formation.code
                subject.recommended_specialisation = (
                    target.specialisation.code if target.specialisation else None
                )
                subject.conversion_stage = ConversionStage.EXPLORATION
            subject.last_intents = intents
            subject.last_scope = facts.scope.value
            subject.last_dialogue_act = act.value
            subject.last_user_message = message
            subject.last_answer_focus = focus_topics(intents)
            subject.covered_topics = list(
                dict.fromkeys((*subject.covered_topics, *subject.last_answer_focus))
            )
            subject.last_answer_text = answer
            return self._finish(
                state,
                message,
                answer,
                intents,
                act,
                first_reply,
                eligibility=eligibility,
                recommendation=recommendation,
            )

        if target and needs_eligibility and eligibility is None:
            eligibility = await self.eligibility_service.evaluate(
                subject,
                target.formation,
                target.specialisation,
            )
            log_stage(
                "ELIGIBILITY",
                session_id=session_id,
                status=eligibility.status.value,
                formation=eligibility.formation_code,
            )

        formation_code = target.formation.code if target else None
        spec_code = target.specialisation.code if target and target.specialisation else None
        if facts.scope is ContextScope.ALL and "FEES" in intents:
            formation_code = None
            spec_code = None
        plan = self.query_planner.plan(
            message,
            intents,
            formation_code=formation_code,
            specialisation_code=spec_code,
        )
        rag_result = await self.rag.retrieve(plan)
        log_stage("RAG_RESULT", session_id=session_id, chunks=len(rag_result.chunks))

        if eligibility and eligibility.status is EligibilityStatus.NOT_ELIGIBLE:
            answer = self.fallback.build(intents, rag_result.facts, recommendation, eligibility)
        else:
            mode = response_mode(intents, act)
            known, forbidden = self.known_facts.build(subject)
            decision_text = self._decision_text(subject, recommendation, eligibility)
            response_messages = self.prompt.compose(
                user_message=message,
                memory=readable_summary(subject, intents),
                known_facts=known,
                forbidden_assumptions=forbidden,
                academic_facts=rag_result.facts,
                decision=decision_text,
                response_mode=mode,
            )
            try:
                answer = await self.llm.generate(
                    "final",
                    response_messages,
                    max_new_tokens=280,
                )
            except Exception:
                logger.warning("FINAL_RESPONSE model unavailable", exc_info=True)
                answer = ""
            answer = self.factual_guard.validate(
                answer,
                rag_result.facts,
                eligibility_status=eligibility.status if eligibility else None,
            )
            if len(answer.split()) < 3:
                answer = self.fallback.build(intents, rag_result.facts, recommendation, eligibility)
            answer = self.repetition_guard.apply(answer, subject.last_answer_text)
            answer = self.length_guard.apply(answer, mode)
            if self.cta.should_add(state, subject, intents, act, recommendation):
                answer = self.cta.add(answer, subject, state.turn_count)
            # CTA and every post-processing result are validated again.
            answer = self.factual_guard.validate(
                answer,
                rag_result.facts,
                eligibility_status=eligibility.status if eligibility else None,
            )
            answer = self.length_guard.apply(answer, mode)

        if recommendation and recommendation.primary:
            subject.recommended_offer = recommendation.primary.formation_code
            subject.recommended_specialisation = recommendation.primary.specialisation_code
            subject.offer_intro_done = True
            subject.last_recommendation_turn = state.turn_count
            subject.conversion_stage = ConversionStage.RECOMMENDATION
        subject.last_intents = intents
        subject.last_scope = facts.scope.value
        subject.last_dialogue_act = act.value
        subject.last_user_message = message
        subject.last_answer_focus = focus_topics(intents)
        subject.covered_topics = list(dict.fromkeys((*subject.covered_topics, *subject.last_answer_focus)))
        subject.last_answer_text = answer
        return self._finish(
            state,
            message,
            answer,
            intents,
            act,
            first_reply,
            eligibility=eligibility,
            recommendation=recommendation,
        )

    def _fixed(
        self,
        message: str,
        state: ConversationState,
        turn_type: TurnType,
        first_reply: bool,
    ) -> DialogueResponse:
        state.turn_count += 1
        answer = self.turn_gate.response(turn_type, first_reply=first_reply)
        state.history.extend((ChatMessage(role="user", content=message), ChatMessage(role="assistant", content=answer)))
        state.touch()
        return DialogueResponse(answer, state)

    def _finish(
        self,
        state: ConversationState,
        message: str,
        answer: str,
        intents: list[str],
        act: DialogueAct,
        first_reply: bool,
        *,
        eligibility: EligibilityDecision | None = None,
        recommendation: RecommendationDecision | None = None,
    ) -> DialogueResponse:
        if first_reply and not answer.lstrip().lower().startswith("salut"):
            answer = "Salut 🙂 " + answer.lstrip()
        elif not first_reply:
            answer = re.sub(
                r"^\s*(?:salut|bonjour|bonsoir|hello|coucou)\s*[!,.🙂😊:-]*\s*",
                "",
                answer,
                count=1,
                flags=re.I,
            )
        state.history.extend((ChatMessage(role="user", content=message), ChatMessage(role="assistant", content=answer)))
        state.touch()
        log_stage("FINAL_RESPONSE", session_id=str(state.session_id), intents=intents, dialogue_act=act.value)
        return DialogueResponse(answer, state, tuple(intents), eligibility, recommendation)

    async def _target_from_recommendation(self, decision: RecommendationDecision) -> AcademicTarget | None:
        option = decision.primary
        if option is None:
            return None
        formation = await self.catalogue.formations.require(option.formation_id)
        spec = await self.catalogue.specialisations.get(option.specialisation_id) if option.specialisation_id else None
        return AcademicTarget(formation, spec)

    async def _remembered_target(self, formation_code: str, spec_code: str | None) -> AcademicTarget | None:
        formation = await self.catalogue.formations.get_by_code(formation_code)
        if formation is None:
            return None
        spec = await self.catalogue.specialisations.get_by_code(spec_code) if spec_code else None
        if spec is not None and spec.formation_id != formation.id:
            spec = None
        return AcademicTarget(formation, spec)

    @staticmethod
    def _decision_text(
        subject: SubjectState,
        recommendation: RecommendationDecision | None,
        eligibility: EligibilityDecision | None,
    ) -> str:
        parts: list[str] = []
        if recommendation and recommendation.primary:
            option = recommendation.primary
            parts.append("Recommandation structurée: " + (option.specialisation_name or option.formation_name))
            parts.extend(recommendation.reasoning)
            if recommendation.challenge:
                parts.append("Défi réaliste: " + recommendation.challenge)
        if subject.profile is AcademicProfile.NEW_BAC and subject.bac_specialty in {"MATH", "SCIENCES"}:
            parts.append(
                "Règle de conseil: après un bac Mathématiques ou Sciences expérimentales, "
                "présenter le Cycle Préparatoire comme voie prioritaire et les licences "
                "confirmées admissibles comme alternatives; ne jamais proposer une admission "
                "directe en cycle ingénieur."
            )
        elif subject.profile is AcademicProfile.NEW_BAC and subject.bac_specialty:
            parts.append(
                f"Règle de conseil: avec un bac {value_label(subject.bac_specialty)}, "
                "présenter uniquement une licence admissible comme parcours d'entrée; "
                "ne jamais proposer une admission directe en cycle ingénieur."
            )
        if eligibility:
            status = {
                EligibilityStatus.ELIGIBLE: "conditions connues satisfaites",
                EligibilityStatus.NOT_ELIGIBLE: "conditions connues non satisfaites",
                EligibilityStatus.UNKNOWN: "admissibilité à confirmer",
            }[eligibility.status]
            parts.append("Vérification d'admission : " + status)
        return "\n".join(parts) or "Répondre directement avec les faits récupérés; ne prendre aucune décision non fondée."
