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
from app.services.academic.target_resolver import (
    AcademicTarget,
    AcademicTargetResolution,
    AcademicTargetResolver,
)
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
from app.services.dialogue.normalizer import fold_text
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
        if (
            state.active_state.pending_action
            and self.pending_slots.is_affirmative(message)
        ):
            turn_type = TurnType.ACADEMIC
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
        strong_academic_signal = bool(
            facts.profile
            or facts.interests
            or self.turn_gate.has_strong_academic_signal(message)
        )
        domain = None
        if not strong_academic_signal:
            try:
                domain = await self.esprit.classify_domain(message)
            except Exception:
                logger.warning("DOMAIN_GATE unavailable", exc_info=True)
        if domain and domain.label == "OUT_OF_SCOPE" and not strong_academic_signal:
            # Some model builds emit a useful label with confidence=0.  A low
            # score therefore changes the wording (clarification vs refusal),
            # but must never let an unrelated request reach the final generator.
            if domain.confidence >= 0.55:
                answer = self._out_of_scope_answer()
                intents = ["OUT_OF_SCOPE"]
            else:
                answer = self._unclear_answer()
                intents = ["GENERAL"]
            return self._finish(
                state,
                message,
                answer,
                intents,
                DialogueAct.ASK_INFORMATION,
                first_reply,
            )
        if domain and domain.label == "UNCLEAR" and not strong_academic_signal:
            return self._finish(
                state,
                message,
                self._unclear_answer(),
                ["GENERAL"],
                DialogueAct.ASK_INFORMATION,
                first_reply,
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
        esprit_result = ""
        act = self.dialogue_acts.detect(
            message,
            auxiliary_interpretation="",
            scope=facts.scope,
            negation=negation,
            pending_parsed=pending.parsed,
        )
        intents = self.intents.detect(
            message,
            auxiliary_interpretation="",
            previous=pending.previous_intents or tuple(subject.last_intents),
            scope=facts.scope,
            dialogue_act=act,
            slot_parsed=pending.parsed,
        )
        if (
            intents == ["GENERAL"]
            and not pending.forced_intents
            and not (facts.profile or facts.interests or facts.target)
        ):
            try:
                esprit_result = await self.esprit.interpret(message)
            except Exception:
                logger.warning("ESPRIT_RESULT unavailable", exc_info=True)
            if esprit_result:
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
        log_stage("ESPRIT_RESULT", session_id=session_id, available=bool(esprit_result))
        if pending.forced_intents:
            intents = list(pending.forced_intents)
        if facts.profile and intents == ["GENERAL"]:
            intents = ["ORIENTATION"]
        if facts.target and intents == ["GENERAL"]:
            intents = ["ORIENTATION"]
        if facts.target == "ENGINEERING":
            subject.recommended_offer = None
            subject.recommended_specialisation = None
            subject.offer_intro_done = False
            intents = ["ORIENTATION"]
        if facts.denies_bac and intents == ["GENERAL"]:
            intents = ["ORIENTATION"]
        if "OUT_OF_SCOPE" in intents:
            answer = self._out_of_scope_answer()
            return self._finish(state, message, answer, ["OUT_OF_SCOPE"], act, first_reply)
        target_resolution = await self.target_resolver.resolve_request(message)
        target = target_resolution.target
        if subject.recommended_offer:
            contextual_target = await self._contextual_specialisation_choice(
                message,
                subject,
            )
            if contextual_target is not None:
                target = contextual_target
                target_resolution = AcademicTargetResolution(target=target)
        if (
            target_resolution.unavailable_label
            and self.target_resolver.is_current_reference(message)
            and subject.recommended_offer
        ):
            target = await self._remembered_target(
                subject.recommended_offer,
                subject.recommended_specialisation,
            )
            if target is not None:
                target_resolution = AcademicTargetResolution(target=target)
        if target_resolution.unavailable_label and intents == ["GENERAL"]:
            intents = ["ORIENTATION"]
        log_stage("INTENTS", session_id=session_id, dialogue_act=act.value, intents=intents)

        if "INFORMATIQUE" in subject.rejected_domains and "ORIENTATION" in intents:
            answer = "D'accord, je n'insiste pas sur l'informatique. Je peux uniquement te proposer une autre formation présente dans le catalogue académique actif, sans en inventer. Quel domaine t'intéresse ?"
            return self._finish(state, message, answer, intents, act, first_reply)

        if (
            "ORIENTATION" in intents
            and subject.target == "ENGINEERING"
            and target is not None
            and target.formation.code.startswith("LICENCE_")
        ):
            target = None
        if (
            "ORIENTATION" in intents
            and subject.profile is AcademicProfile.PREPA_HOLDER
            and target is not None
            and target.formation.code == "PREPA_GENERAL"
        ):
            target = None
        if target is not None and intents == ["GENERAL"]:
            intents = ["DETAILS"]
        elif facts.interests and intents == ["GENERAL"]:
            intents = ["ORIENTATION"]
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
                if alternative and alternative.primary:
                    subject.recommended_offer = alternative.primary.formation_code
                    subject.recommended_specialisation = (
                        alternative.primary.specialisation_code
                    )
                    subject.offer_intro_done = True
                    subject.last_recommendation_turn = state.turn_count
                    subject.conversion_stage = ConversionStage.RECOMMENDATION
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
        if (
            target is None
            and subject.recommended_offer
            and not (
                facts.scope is ContextScope.ALL
                and "FEES" in intents
            )
        ):
            target = await self._remembered_target(subject.recommended_offer, subject.recommended_specialisation)

        if target is not None and self._asks_specialisation_list(message):
            # "Quelles sont les spécialités ?" asks for siblings of the current
            # option, not for another repetition of the selected option.
            target = AcademicTarget(target.formation)

        if "ORIENTATION" in intents and recommendation is not None and recommendation.primary is None:
            answer = self.structured.no_confirmed_orientation(subject)
            return self._finish(state, message, answer, intents, act, first_reply)

        structured_answer: str | None = None
        structured_intents = {
            "CATALOG", "FEES", "REGISTRATION_DOCUMENTS", "ACCREDITATION",
            "PERSUASION", "LOCATION", "CONTACT", "SCHEDULE",
        }
        requested_structured = structured_intents.intersection(intents)
        target_specific_intents = {
            "DETAILS",
            "PROGRAMME",
            "CAREERS",
            "MARKET",
            "CERTIFICATIONS",
            "INTERNATIONAL",
            "DURATION",
            "DIFFICULTY",
            "ADMISSION",
        }
        if (
            target is None
            and not target_resolution.unavailable_label
            and target_specific_intents.intersection(intents)
        ):
            structured_answer = self.structured.missing_formation_for_details()
        elif len(requested_structured) > 1:
            blocks: list[str] = []
            all_licences = target is None and self._asks_all_licence_tariffs(message)
            if "CATALOG" in requested_structured:
                blocks.append(await self.structured.catalogue_overview(message))
            if "FEES" in requested_structured:
                blocks.append(await self.structured.fees(
                    target,
                    include_all=(
                        facts.scope is ContextScope.ALL
                        or all_licences
                        or "CATALOG" in requested_structured
                    ),
                    licence_only=all_licences,
                ))
            if "ACCREDITATION" in requested_structured:
                blocks.append(await self.structured.accreditation(target, message))
            if "PERSUASION" in requested_structured:
                blocks.append(await self.structured.institutional_advantages())
            if "LOCATION" in requested_structured or "CONTACT" in requested_structured:
                blocks.append(await self.structured.location())
            if "SCHEDULE" in requested_structured:
                blocks.append(await self.structured.schedule())
            if "REGISTRATION_DOCUMENTS" in requested_structured:
                blocks.append(await self.structured.registration_documents(
                    target,
                    pre_registration_completed=subject.pre_registration_completed,
                ))
            structured_answer = "\n\n".join(blocks)
        elif target_resolution.unavailable_label and not ({"LOCATION", "CONTACT"} & set(intents)):
            structured_answer = self.structured.unavailable_formation(
                target_resolution.unavailable_label,
                subject,
                recommendation,
            )
        elif "CATALOG" in intents:
            structured_answer = await self.structured.catalogue_overview(message)
        elif "FEES" in intents:
            all_licences = target is None and self._asks_all_licence_tariffs(message)
            structured_answer = await self.structured.fees(
                target,
                include_all=facts.scope is ContextScope.ALL or all_licences,
                licence_only=all_licences,
            )
        elif "REGISTRATION_DOCUMENTS" in intents:
            structured_answer = await self.structured.registration_documents(
                target,
                pre_registration_completed=subject.pre_registration_completed,
            )
        elif "PROFILE_RECALL" in intents:
            structured_answer = self.structured.profile_summary(subject)
        elif "ACCREDITATION" in intents:
            structured_answer = await self.structured.accreditation(target, message)
        elif "PERSUASION" in intents:
            structured_answer = await self.structured.institutional_advantages()
        elif "LOCATION" in intents or "CONTACT" in intents:
            structured_answer = await self.structured.location()
        elif "SCHEDULE" in intents:
            structured_answer = await self.structured.schedule()
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
                structured_answer = await self.structured.formation_details(
                    target,
                    intents,
                    include_all=facts.scope is ContextScope.ALL,
                )

        if structured_answer:
            answer = structured_answer
            if recommendation and recommendation.primary:
                subject.recommended_offer = recommendation.primary.formation_code
                subject.recommended_specialisation = recommendation.primary.specialisation_code
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
            subject.pending_action = self._next_pending_action(
                intents,
                target=target,
            )
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

        # GENERAL is an unresolved routing result, not permission to improvise.
        # Keeping it away from the final generator is the last-resort
        # anti-hallucination boundary when NLU is unavailable or uncertain.
        if intents == ["GENERAL"]:
            return self._finish(
                state,
                message,
                self._unclear_answer(),
                intents,
                act,
                first_reply,
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
            known, forbidden = self.known_facts.build(
                subject,
                include_profile=bool(
                    {"ORIENTATION", "ADMISSION", "PREINSCRIPTION"}.intersection(intents)
                ),
            )
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
            recent_answers = tuple(
                item.content
                for item in state.history[-10:]
                if item.role == "assistant"
            )
            answer = self.repetition_guard.apply(
                answer,
                subject.last_answer_text,
                recent_answers,
            )
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

    @staticmethod
    def _next_pending_action(
        intents: list[str],
        *,
        target: AcademicTarget | None,
    ) -> str | None:
        if "PREINSCRIPTION" in intents or "PROFILE_RECALL" in intents:
            return None
        if "FEES" in intents:
            return "PREINSCRIPTION"
        if "DIFFICULTY" in intents or "ORIENTATION" in intents:
            return "PROGRAMME"
        if {"PROGRAMME", "DETAILS"}.intersection(intents):
            if target is not None and target.specialisation is None:
                return None
            return "PREINSCRIPTION"
        if {"CAREERS", "MARKET", "CERTIFICATIONS", "INTERNATIONAL"}.intersection(intents):
            return "PREINSCRIPTION"
        return None

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
        if not first_reply:
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

    @staticmethod
    def _out_of_scope_answer() -> str:
        return (
            "Je peux aider uniquement pour les formations, l'orientation, "
            "l'admission, les modules, les frais et les informations officielles de l'IIT."
        )

    @staticmethod
    def _unclear_answer() -> str:
        return (
            "Je n'ai pas suffisamment compris la demande. Peux-tu préciser la formation ou "
            "l'information IIT recherchée : programme, admission, tarifs, accréditation ou emplacement ?"
        )

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
    def _asks_all_licence_tariffs(message: str) -> bool:
        text = re.sub(r"\s+", " ", message.lower()).strip()
        return bool(
            re.search(r"\blicence(?:s)?\b", text)
            and not re.search(
                r"\blicence(?:s)?\s+(?:en|de|d')?\s*[a-z0-9]",
                text,
            )
        )

    @staticmethod
    def _asks_specialisation_list(message: str) -> bool:
        text = fold_text(message)
        return bool(
            re.search(
                r"\b(?:quelles?|liste|chnouma|chneya)\b.{0,24}"
                r"\b(?:specialites?|options?|filieres?)\b",
                text,
            )
            or re.search(
                r"\b(?:specialites?|options?|filieres?)\s+(?:disponibles?|proposees?)\b",
                text,
            )
        )

    async def _contextual_specialisation_choice(
        self,
        message: str,
        subject: SubjectState,
    ) -> AcademicTarget | None:
        text = fold_text(message)
        offer = subject.recommended_offer or ""
        if "licence" in text and offer != "LICENCE_INFO":
            return None
        if (
            re.search(r"\b(?:cycle\s+ingenieur|ingenieur\s+informatique)\b", text)
            and offer != "INGENIEUR_INFO"
        ):
            return None

        if any(term in text for term in ("logiciel", "glid", "glsi", "decisionnelle")):
            family = "SOFTWARE"
        elif any(term in text for term in ("cyber", "reseau", "arsi")):
            family = "CYBER"
        elif any(
            term in text for term in ("data", "intelligence artificielle", "sdia")
        ) or re.search(r"\bia\b", text):
            family = "DATA_AI"
        elif any(term in text for term in ("iot", "embarque")):
            family = "IOT"
        else:
            return None

        spec_code = {
            ("INGENIEUR_INFO", "SOFTWARE"): "GLID",
            ("INGENIEUR_INFO", "CYBER"): "ARSI",
            ("INGENIEUR_INFO", "DATA_AI"): "SDIA",
            ("LICENCE_INFO", "SOFTWARE"): "LIC_INFO_GLSI",
            ("LICENCE_INFO", "CYBER"): "LIC_INFO_CYBER",
            ("LICENCE_INFO", "DATA_AI"): "LIC_INFO_BIG_DATA",
            ("LICENCE_INFO", "IOT"): "LIC_INFO_IOT",
        }.get((offer, family))
        if spec_code is None:
            return None
        return await self._remembered_target(offer, spec_code)

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
                "présenter d'abord les licences confirmées admissibles, puis le Cycle "
                "Préparatoire comme autre voie possible; ne jamais proposer une admission "
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
