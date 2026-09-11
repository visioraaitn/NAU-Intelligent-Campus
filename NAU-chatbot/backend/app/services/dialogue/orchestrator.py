from __future__ import annotations

import logging
import re
from copy import deepcopy
from dataclasses import dataclass, replace

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
    RecommendationOption,
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
from app.services.dialogue.structured_response import FORMATION_LINKS, StructuredResponseBuilder
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
        if (
            state.active_state.pending_slot
            and len(message.split()) <= 2
            and turn_type is TurnType.SMALL_TALK
        ):
            # Short answers such as "infoo" or "indus" respond to the
            # qualification question and must not be diverted to social NLU.
            turn_type = TurnType.ACADEMIC
        session_id = str(state.session_id)
        log_stage("TURN_GATE", session_id=session_id, turn_type=turn_type.value)

        if turn_type is TurnType.RESET:
            reset = ConversationState.new(state.session_id)
            return self._fixed(message, reset, turn_type, first_reply)
        if turn_type in {TurnType.SECURITY, TurnType.INAPPROPRIATE, TurnType.EMPTY}:
            # Refusal gates do not mutate academic or conversational profile memory.
            return DialogueResponse(self.turn_gate.response(turn_type, first_reply=first_reply), state)
        if not state.active_state.pending_action and self.pending_slots.is_affirmative(message):
            return self._fixed(message, state, TurnType.SMALL_TALK, first_reply)
        original_state = state.model_copy(deep=True)
        semantic = None
        semantic_context = (
            f"Formation évoquée : {state.active_state.recommended_offer or 'non précisée'}. "
            f"Spécialisation : {state.active_state.recommended_specialisation or 'non précisée'}."
        ) if state.active_state.recommended_offer else ""
        if len(message.split()) <= 2:
            # A previous answer must not give an unrelated short token a new
            # meaning. The normal target-memory path resolves the scope later.
            semantic_context = ""
        if turn_type is TurnType.SMALL_TALK:
            try:
                semantic = await self.esprit.understand_social(message)
            except Exception:
                logger.warning("SOCIAL_UNDERSTANDING unavailable")
            try:
                semantic = semantic or await self.esprit.understand(message, semantic_context)
            except Exception:
                logger.warning("SEMANTIC_UNDERSTANDING unavailable")
            if semantic and semantic.domain.confidence >= .8:
                if semantic.domain.label == "INAPPROPRIATE":
                    return self._refuse_inappropriate(state, original_state)
                if semantic.domain.label == "SOCIAL" and semantic.social:
                    return self._fixed(message, state, TurnType(semantic.social), first_reply)
                if semantic.domain.label == "IN_SCOPE" and semantic.domain.iit_signal:
                    turn_type = TurnType.ACADEMIC
                elif semantic.domain.label == "OUT_OF_SCOPE" and len(message.split()) > 2:
                    return self._fixed(message, state, TurnType.OUT_OF_SCOPE, first_reply)
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
        turn_subject = state.subjects[facts.subject]
        if facts.subject != state.active_subject:
            semantic_context = (
                f"Formation évoquée : {turn_subject.recommended_offer}. "
                f"Spécialisation : {turn_subject.recommended_specialisation or 'non précisée'}."
            ) if turn_subject.recommended_offer else ''
        # A pending question concerns the original diploma, not an IIT offer.
        # Only interpret a free-form answer when it has no explicit new topic.
        early_target = await self.target_resolver.resolve_request(message)
        raw_intents = self.intents.detect(message, previous=(), scope=ContextScope.CURRENT,
                                         dialogue_act=DialogueAct.ASK_INFORMATION, slot_parsed=False)
        if (facts.profile is AcademicProfile.NEW_BAC and raw_intents != ['GENERAL']
                and not facts.correction and facts.subject == state.active_subject
                and re.search(r'\bpour (?:un|le|les) bac\b', fold_text(message))):
            # A question about entry requirements/costs for a type of bac is
            # not a new claim about the speaker's current qualification.
            facts = replace(facts, profile=None, bac_specialty=None,
                            bac_average=None, math_grade=None)
        if (
            facts.profile is AcademicProfile.NEW_BAC
            and facts.bac_specialty
            and state.active_state.profile
            in {AcademicProfile.LICENCE_STUDENT, AcademicProfile.LICENCE_HOLDER}
            and not facts.correction
            and facts.subject == state.active_subject
        ):
            # A bac section can complete a higher-level profile; it is not
            # automatically a correction of the student's current degree.
            facts = replace(facts, profile=None)
        existing_credential = fold_text((state.active_state.licence_specialty or '').replace('_', ' '))
        clarifies_credential = state.active_state.pending_slot in {'LICENCE_SPECIALTY', 'PROFILE_CONFIRMATION'} or (existing_credential and existing_credential in fold_text(message))
        if clarifies_credential and state.active_state.profile in {AcademicProfile.LICENCE_STUDENT, AcademicProfile.LICENCE_HOLDER} and not (facts.profile or facts.target or early_target.target) and raw_intents == ['GENERAL']:
            specialty = facts.licence_specialty
            if not specialty:
                try:
                    specialty = await self.esprit.understand_credential(message)
                except Exception:
                    logger.warning('CREDENTIAL_UNDERSTANDING unavailable')
            if specialty:
                facts = replace(facts, licence_specialty=specialty, credential_answer=True)
        if state.active_state.pending_slot == 'PROFILE_CONFIRMATION' and facts.profile and facts.subject == state.active_subject:
            facts = replace(facts, correction=True)
        elif (facts.profile and facts.profile.rank < state.active_state.profile.rank
              and not facts.correction and facts.subject == state.active_subject):
            state.active_state.pending_slot = 'PROFILE_CONFIRMATION'
            answer = (self.structured.profile_summary(state.active_state)
                      + " Tu évoques maintenant un autre niveau. Est-ce une correction de ton niveau actuel ? "
                      "Précise ton niveau actuel : bac, licence en cours ou licence obtenue, par exemple.")
            state.active_state.last_question_asked = answer
            return self._finish(state, message, answer, ['ORIENTATION'], DialogueAct.ANSWER_SLOT, first_reply)
        if raw_intents == ['GENERAL'] and early_target.target is not None and not (facts.profile or facts.target):
            # Resolve an explicit catalogue selection before a fallible model
            # can broaden it into a request for all formations.
            raw_intents = ['DETAILS']
        contextual_intents = self.intents.detect(
            message, previous=(), scope=ContextScope.CURRENT,
            dialogue_act=DialogueAct.ASK_INFORMATION, slot_parsed=False,
        ) if turn_subject.recommended_offer else []
        strong_academic_signal = bool(
            facts.profile
            or facts.interests
            or facts.licence_specialty
            or early_target.target is not None
            or (len(message.split()) == 1 and raw_intents != ['GENERAL'])
            or (
                facts.scope is ContextScope.ALL
                and self.intents.context.is_elliptical_expansion(message)
                and set(turn_subject.last_intents).difference({"GENERAL", "OUT_OF_SCOPE"})
            )
            or (state.active_state.pending_action and self.pending_slots.is_affirmative(message))
            or (
                state.active_state.pending_slot
                and self.pending_slots.resolve(message, deepcopy(state.active_state)).parsed
            )
            or re.fullmatch(r"(?:nhebek\s+)?(?:tensahni|tansahni|chtansahni)[ ?.!]*", fold_text(message))
            or self.turn_gate.has_strong_academic_signal(message)
            or (
                turn_subject.recommended_offer
                and set(contextual_intents).intersection({
                    "FEES", "PROGRAMME", "CERTIFICATIONS", "PRACTICE", "PROJECTS", "DURATION",
                    "INTERNSHIPS", "ALTERNANCE", "LOCATION", "SCHEDULE", "CAREERS",
                    "ACCREDITATION", "PREINSCRIPTION", "CONTACT", "PAYMENT", "ADMISSION",
                })
            )
        )
        domain = None
        if not strong_academic_signal:
            try:
                semantic = semantic or await self.esprit.understand(message, semantic_context)
                domain = semantic.domain
                if domain.confidence < .8:
                    semantic = None
                    domain = None
            except Exception:
                logger.warning("SEMANTIC_UNDERSTANDING unavailable")
            if domain is None:
                try:
                    domain = await self.esprit.classify_domain(message)
                except Exception:
                    logger.warning("DOMAIN_GATE unavailable", exc_info=True)
        if domain and domain.label == "INAPPROPRIATE":
            return self._refuse_inappropriate(state, original_state)
        if domain and domain.label == "SOCIAL" and semantic and semantic.social:
            return self._fixed(message, state, TurnType(semantic.social), first_reply)
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
        previous_scope = state.active_state.last_scope if facts.subject == state.active_subject else ContextScope.CURRENT.value
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

        pending = self.pending_slots.resolve(message, subject, provided_fields={
            name for name in ('licence_specialty', 'profile', 'bac_specialty') if getattr(facts, name) is not None
            and (name != 'licence_specialty' or facts.profile is not None or facts.credential_answer)
        })
        all_paths_requested = self._asks_all_paths(message) or (pending.parsed and previous_scope == ContextScope.ALL.value)
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
        if raw_intents == ['DETAILS'] and intents == ['GENERAL']:
            intents = ['DETAILS']
        if facts.licence_specialty and subject.profile in {AcademicProfile.LICENCE_STUDENT, AcademicProfile.LICENCE_HOLDER} and raw_intents == ['GENERAL']:
            intents = ['ORIENTATION']
        if (facts.profile or facts.target) and intents == ['GENERAL']:
            intents = ['ORIENTATION']
        if semantic is None and intents in (["GENERAL"], ["DETAILS"]) and len(message.split()) >= 5 and not pending.parsed and early_target.target is None:
            try:
                semantic = await self.esprit.understand(message, semantic_context)
            except Exception:
                logger.warning("SEMANTIC_UNDERSTANDING unavailable")
        if semantic and semantic.domain.label == "INAPPROPRIATE" and semantic.domain.confidence >= .8:
            return self._refuse_inappropriate(state, original_state)
        if intents in (["GENERAL"], ["DETAILS"]) and semantic and semantic.domain.label == "IN_SCOPE" and semantic.domain.confidence >= .8 and semantic.intents:
            # Model intents are validated against the contract; no spelling
            # variant or regex is needed to route an unfamiliar expression.
            normalized_intents = self.intents.detect(
                semantic.normalized, previous=(), scope=ContextScope.CURRENT,
                dialogue_act=DialogueAct.ASK_INFORMATION, slot_parsed=False,
            )
            intents = list(dict.fromkeys(
                [intent for intent in intents if intent != "GENERAL"]
                + list(semantic.intents)
                + [intent for intent in normalized_intents if intent in {
                    "PRACTICE", "PROJECTS", "INTERNSHIPS", "CERTIFICATIONS",
                    "FEES", "DURATION", "ALTERNANCE",
                }]
            ))
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
        if "CATALOG" in intents and re.search(r"\b(?:pour moi|que je|ne[jg]+em|na[jg]+em)\b", fold_text(message)):
            intents = ["ORIENTATION" if intent == "CATALOG" else intent for intent in intents]
        if facts.profile and intents == ["GENERAL"]:
            intents = ["ORIENTATION"]
        if facts.target and intents == ["GENERAL"]:
            intents = ["ORIENTATION"]
        if facts.target == "ENGINEERING":
            subject.recommended_offer = None
            subject.recommended_specialisation = None
            subject.offer_intro_done = False
            if intents == ['GENERAL']:
                intents = ['ORIENTATION']
        if facts.denies_bac and intents == ["GENERAL"]:
            intents = ["ORIENTATION"]
        if "OUT_OF_SCOPE" in intents:
            answer = self._out_of_scope_answer()
            return self._finish(state, message, answer, ["OUT_OF_SCOPE"], act, first_reply)
        target_resolution = early_target
        if (
            target_resolution.target is None and not target_resolution.unavailable_label
            and semantic and semantic.domain.label == "IN_SCOPE"
            and semantic.domain.confidence >= .8 and semantic.normalized
        ):
            target_resolution = await self.target_resolver.resolve_request(semantic.normalized)
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
        if (
            target is None and subject.recommended_offer
            and not target_resolution.unavailable_label
            and not {"ORIENTATION", "CATALOG"}.intersection(intents)
            and not (facts.scope is ContextScope.ALL and "FEES" in intents)
        ):
            target = await self._remembered_target(subject.recommended_offer, subject.recommended_specialisation)
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
        qualification_question = None
        slot = self.qualification.choose(subject, intents)
        if slot and (
            subject.asked_slots.get(slot, 0) == 0
            or subject.pending_slot == slot
        ):
            question = self.qualification.ask(slot, subject, state.turn_count)
            subject.last_intents = intents
            subject.last_scope = ContextScope.ALL.value if all_paths_requested else facts.scope.value
            subject.last_dialogue_act = act.value
            subject.last_user_message = message
            subject.conversion_stage = ConversionStage.QUALIFICATION
            if not set(intents).difference({"ORIENTATION", "GENERAL", "DETAILS"}):
                return self._finish(state, message, question, intents, act, first_reply)
            qualification_question = question

        recommendation: RecommendationDecision | None = None
        credential_options = await self.structured.credential_options(subject) if 'ORIENTATION' in intents else []
        if credential_options:
            recommendation = RecommendationDecision(None, None)
        elif not qualification_question and ("ORIENTATION" in intents or ("PREINSCRIPTION" in intents and target is None)):
            if target is not None and "ORIENTATION" in intents:
                # An explicit formation request must not be replaced by the
                # highest-scoring sibling (for example Génie Industriel when
                # the student explicitly asked for Génie Informatique).
                target_eligibility = eligibility or await self.eligibility_service.evaluate(
                    subject,
                    target.formation,
                    target.specialisation,
                )
                recommendation = RecommendationDecision(
                    RecommendationOption(
                        formation_id=target.formation.id,
                        formation_code=target.formation.code,
                        formation_name=target.formation.nom,
                        specialisation_id=(
                            target.specialisation.id if target.specialisation else None
                        ),
                        specialisation_code=(
                            target.specialisation.code if target.specialisation else None
                        ),
                        specialisation_name=(
                            target.specialisation.nom if target.specialisation else None
                        ),
                        score=2.0,
                        eligibility=target_eligibility,
                    ),
                    None,
                )
            else:
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

        if "ORIENTATION" in intents and recommendation is not None and recommendation.primary is None and not all_paths_requested:
            answer = self.structured.no_confirmed_orientation(subject, credential_options)
            if credential_options:
                subject.pending_slot = 'LICENCE_SPECIALTY'
                subject.last_question_asked = "Quel intitulé exact figure sur ton diplôme ou ton attestation de licence ?"
                if original_state.active_state.pending_slot in {'LICENCE_SPECIALTY', 'PROFILE_CONFIRMATION'}:
                    if facts.target == 'ENGINEERING':
                        answer = "D'accord, tu vises un cycle ingénieur. Pour vérifier les possibilités avec ta licence, donne-moi son intitulé complet : " + ", ".join(credential_options) + " ou une autre spécialité ?"
                    elif facts.profile is AcademicProfile.LICENCE_HOLDER:
                        answer = "D'accord, ta licence est validée. Il reste à préciser sa spécialité exacte : " + ", ".join(credential_options) + " ou un autre intitulé ?"
                    elif facts.licence_specialty:
                        answer = "Je comprends le domaine industriel. Pour l'admission, quelle spécialité précise as-tu suivie : " + ", ".join(credential_options) + " ou une autre ?"
            subject.last_answer_text = answer
            subject.last_intents = intents
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
            "DIFFICULTY", "PRACTICE", "PROJECTS", "INTERNSHIPS",
            "ADMISSION",
        }
        if (
            target is None
            and not target_resolution.unavailable_label
            and target_specific_intents.intersection(intents)
            and not requested_structured
        ):
            structured_answer = self.structured.missing_formation_for_details()
        elif len(set(intents).difference({"GENERAL", "DETAILS"})) > 1:
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
            if "PAYMENT" in intents and "FEES" not in intents:
                blocks.append(await self.structured.fees(target))
            if "ALTERNANCE" in intents:
                blocks.append(await self.structured.alternance(target))
            if target is not None and target_specific_intents.difference({"ADMISSION"}).intersection(intents):
                blocks.append(await self._formation_details_for_turn(target, intents, state, message, include_all=facts.scope is ContextScope.ALL))
            elif target is None and target_specific_intents.intersection(intents):
                blocks.append(self.structured.missing_formation_for_details())
            if "ADMISSION" in intents and target is not None:
                blocks.append(await self.structured.admission(target, subject, eligibility))
            if "ORIENTATION" in intents and recommendation is not None:
                orientation = await self._all_eligible_paths(subject) if all_paths_requested else await self.structured.orientation(subject, recommendation)
                if orientation:
                    blocks.append(orientation)
            if "PREINSCRIPTION" in intents and target is not None and not (eligibility and eligibility.status is EligibilityStatus.NOT_ELIGIBLE):
                blocks.append(await self.structured.pre_registration(target))
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
        elif "ALTERNANCE" in intents:
            structured_answer = await self.structured.alternance(target)
        elif "PAYMENT" in intents:
            structured_answer = await self.structured.fees(target)
        elif "ADMISSION" in intents and target is not None:
            structured_answer = await self.structured.admission(target, subject, eligibility)
        elif "ORIENTATION" in intents and recommendation is not None:
            structured_answer = await self.structured.orientation(subject, recommendation)
            if all_paths_requested:
                structured_answer = await self._all_eligible_paths(subject)
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
            "DIFFICULTY", "PRACTICE", "PROJECTS", "INTERNSHIPS",
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
                structured_answer = await self._formation_details_for_turn(
                    target,
                    intents,
                    state,
                    message,
                    include_all=facts.scope is ContextScope.ALL,
                )

        if structured_answer:
            answer = structured_answer
            if eligibility and eligibility.status is EligibilityStatus.NOT_ELIGIBLE:
                answer += (
                    "\n\nRemarque : les critères publiés ne correspondent pas aux informations "
                    "actuellement connues de ton profil. Cela ne bloque pas ta demande : "
                    "l'administration IIT peut étudier ton dossier et te confirmer les possibilités."
                )
                answer = '\n'.join(line for line in answer.splitlines()
                                   if not (line.startswith(('Veux-tu', 'Souhaites-tu'))
                                           and 'pre inscription' in fold_text(line)))
            if len(set(intents).difference({"GENERAL", "DETAILS"})) > 1:
                answer = self._single_followup(answer)
            if qualification_question:
                answer = self._single_followup(answer, keep_last=False) + "\n" + qualification_question
            elif not {"ORIENTATION", "PREINSCRIPTION"}.intersection(intents) and state.turn_count - subject.last_recommendation_turn < 3 and subject.last_answer_text:
                answer = self._single_followup(answer, keep_last=False)
            registration_followup = any(
                line.startswith(("Veux-tu", "Souhaites-tu")) and "pre inscription" in fold_text(line)
                for line in answer.splitlines()
            )
            if registration_followup and "PREINSCRIPTION" not in intents:
                if subject.last_cta_turn > 0 and state.turn_count - subject.last_cta_turn < 3:
                    answer = self._single_followup(answer, keep_last=False)
                else:
                    subject.last_cta_turn = state.turn_count
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
                "DIFFICULTY", "PRACTICE", "PROJECTS", "INTERNSHIPS", "ADMISSION", "FEES",
            }.intersection(intents):
                subject.recommended_offer = target.formation.code
                subject.recommended_specialisation = (
                    target.specialisation.code if target.specialisation else None
                )
                subject.conversion_stage = ConversionStage.EXPLORATION
            subject.pending_action = self._next_pending_action(
                intents,
                target=target,
            ) if any(line.startswith(("Veux-tu", "Souhaites-tu")) for line in answer.splitlines()) else None
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

        if (
            eligibility
            and eligibility.status is EligibilityStatus.NOT_ELIGIBLE
            and target is None
        ):
            # Eligibility is normally evaluated only with a concrete target.
            # Keep the fallback as a defensive path if that invariant changes.
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
            if (
                eligibility
                and eligibility.status is EligibilityStatus.NOT_ELIGIBLE
                and "Remarque :" not in answer
            ):
                answer += (
                    "\n\nRemarque : les critères publiés ne correspondent pas aux informations "
                    "actuellement connues de ton profil. Cela ne bloque pas ta demande : "
                    "l'administration IIT peut étudier ton dossier et te confirmer les possibilités."
                )

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
    def _refuse_inappropriate(state: ConversationState, original: ConversationState) -> DialogueResponse:
        for field in ConversationState.model_fields:
            setattr(state, field, getattr(original, field))
        return DialogueResponse(TurnGate().response(TurnType.INAPPROPRIATE, first_reply=False), state)

    async def _formation_details_for_turn(self, target, intents, state, message, *, include_all=False):
        subject = state.active_state
        continuing = (
            subject.recommended_offer == target.formation.code
            and subject.recommended_specialisation == (target.specialisation.code if target.specialisation else None)
            and bool(state.history)
        )
        source = FORMATION_LINKS.get(target.formation.code, "https://iit.tn/formation/")
        source_seen = any(source in item.content for item in state.history if item.role == "assistant")
        source_requested = bool({"lien", "source", "sources", "site", "page"}.intersection(fold_text(message).split()))
        return await self.structured.formation_details(
            target, intents, include_all=include_all, continuing=continuing,
            show_source=source_requested or not continuing or not source_seen,
            show_specialisations=not continuing or self._asks_specialisation_list(message),
        )

    @staticmethod
    def _asks_all_paths(message: str) -> bool:
        text = fold_text(message)
        return bool(re.search(r"\b(?:tous|toutes|tout|kol|koll)\b", text) and re.search(r"\b(?:parcours|formations|voies|filieres)\b", text))

    async def _all_eligible_paths(self, subject: SubjectState) -> str:
        from app.repositories.academic import PageRequest
        formations = (await self.catalogue.formations.list(PageRequest(page_size=100))).items
        confirmed, uncertain = [], []
        for formation in formations:
            if subject.profile is AcademicProfile.NEW_BAC and formation.code.startswith("INGENIEUR_"):
                continue
            decision = await self.eligibility_service.evaluate(subject, formation)
            label = formation.nom + (f" — {formation.duree_annees} ans" if formation.duree_annees else "")
            if decision.status is EligibilityStatus.ELIGIBLE:
                confirmed.append("• " + label)
            elif decision.status is EligibilityStatus.UNKNOWN:
                uncertain.append("• " + label)
        blocks = ["Voici les parcours compatibles avec les critères actuellement connus de ton profil :", *confirmed] if confirmed else ["Aucun parcours n'est confirmé avec les informations actuellement disponibles."]
        if uncertain:
            blocks.extend(["À vérifier séparément avec l'IIT, faute d'informations suffisantes :", *uncertain])
        blocks.append("La compatibilité avec les critères ne garantit pas l'admission finale. Quel parcours veux-tu comparer ou approfondir ?")
        return "\n".join(blocks)

    @staticmethod
    def _single_followup(answer: str, *, keep_last: bool = True) -> str:
        lines = answer.splitlines()
        questions = [i for i, line in enumerate(lines) if line.startswith(("Veux-tu", "Souhaites-tu", "Dis-moi", "Laquelle", "Parmi ces"))]
        removed = set(questions[:-1] if keep_last else questions)
        return "\n".join(line for i, line in enumerate(lines) if i not in removed).strip()

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
        if turn_type is TurnType.CLARIFICATION:
            subject = state.active_state
            if subject.pending_slot == 'LICENCE_SPECIALTY':
                answer = ("Les conditions d'accès dépendent de la spécialité exacte de ta licence. "
                          "Il faut l'intitulé complet pour comparer ton diplôme aux conditions publiées, sans supposer une équivalence. "
                          "Quel intitulé complet figure sur ton diplôme ou ton attestation ?")
            elif subject.pending_slot and subject.last_question_asked:
                answer = "Pour continuer, il me manque cette précision : " + subject.last_question_asked
            elif not state.history:
                answer = "Je n'ai pas compris ce message. Tu peux écrire ta question sur les études ou les formations de l'IIT ?"
            elif subject.last_answer_text:
                answer = "Quel élément de ma réponse veux-tu que je précise ? Tu peux le citer, même en quelques mots."
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
