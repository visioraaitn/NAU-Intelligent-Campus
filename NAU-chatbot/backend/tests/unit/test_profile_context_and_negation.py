from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.conversation.models import (
    AcademicProfile,
    ConversationState,
    ConversationSubject,
)
from app.services.dialogue.contextual_modifier import (
    ContextScope,
    ContextualModifierDetector,
)
from app.services.dialogue.dialogue_act_detector import DialogueAct, DialogueActDetector
from app.services.dialogue.negation_detector import NegationDetector
from app.services.dialogue.known_facts_builder import KnownFactsBuilder
from app.services.dialogue.pending_slot_resolver import PendingSlotResolver
from app.services.dialogue.profile_resolver import ProfileResolver
from app.services.dialogue.raw_fact_extractor import RawFactExtractor


pytestmark = pytest.mark.unit


def test_word_boundaries_prevent_information_and_duration_false_positives() -> None:
    extractor = RawFactExtractor()
    negation = NegationDetector().detect("Je veux des informations sur la durée")

    facts = extractor.extract(
        "Je veux des informations sur la durée",
        active_subject=ConversationSubject.SELF,
        negation=negation,
    )
    act = DialogueActDetector().detect(
        "Quelle est la durée ?",
        scope=ContextScope.CURRENT,
        negation=NegationDetector().detect("Quelle est la durée ?"),
        pending_parsed=False,
    )

    assert facts.bac_specialty is None
    assert act is DialogueAct.ASK_INFORMATION


def _extract(
    message: str,
    state: ConversationState,
):
    negation = NegationDetector().detect(message)
    facts = RawFactExtractor().extract(
        message,
        active_subject=state.active_subject,
        negation=negation,
    )
    return facts, negation


def test_profile_priority_prevents_an_uncorrected_downgrade() -> None:
    state = ConversationState.new(uuid4())
    resolver = ProfileResolver()

    facts, negation = _extract("j ai un master en informatique", state)
    resolver.apply(state, facts, negation)
    assert state.active_state.profile is AcademicProfile.MASTER_HOLDER

    lower_facts, lower_negation = _extract("je suis bac math", state)
    resolver.apply(state, lower_facts, lower_negation)

    assert state.active_state.profile is AcademicProfile.MASTER_HOLDER
    assert state.active_state.bac_specialty == "MATH"


def test_explicit_correction_can_replace_a_higher_ranked_profile() -> None:
    state = ConversationState.new(uuid4())
    state.active_state.profile = AcademicProfile.MASTER_HOLDER
    facts, negation = _extract("non je suis en licence informatique", state)

    ProfileResolver().apply(state, facts, negation)

    assert facts.correction is True
    assert state.active_state.profile is AcademicProfile.LICENCE_STUDENT


@pytest.mark.parametrize(
    "message",
    [
        "ena njaht fel licence",
        "j'ai réussi ma licence",
        "j ai valide ma licence",
        "j'ai obtenu ma licence",
    ],
)
def test_successfully_completed_licence_is_a_holder_profile(message: str) -> None:
    state = ConversationState.new(uuid4())
    facts, negation = _extract(message, state)

    ProfileResolver().apply(state, facts, negation)

    assert facts.profile is AcademicProfile.LICENCE_HOLDER
    assert state.active_state.profile is AcademicProfile.LICENCE_HOLDER


def test_completed_licence_statement_does_not_create_a_fake_specialty() -> None:
    facts, _ = _extract("ya weldi ena njaht fel licence sayey", ConversationState.new(uuid4()))

    assert facts.profile is AcademicProfile.LICENCE_HOLDER
    assert facts.licence_specialty is None


def test_explicit_bac_denial_clears_a_previous_new_bac_profile() -> None:
    state = ConversationState.new(uuid4())
    subject = state.active_state
    subject.profile = AcademicProfile.NEW_BAC
    subject.bac_specialty = "SCIENCES"
    subject.bac_average = 14
    subject.math_grade = 12
    subject.math_comfort = "MEDIUM"

    facts, negation = _extract("manich bac", state)
    ProfileResolver().apply(state, facts, negation)

    assert facts.denies_bac is True
    assert state.active_state.profile is AcademicProfile.UNKNOWN
    assert state.active_state.bac_specialty is None
    assert state.active_state.bac_average is None
    assert state.active_state.math_grade is None


def test_bac_denial_is_not_a_new_bac_fact() -> None:
    facts, _ = _extract("manich bac", ConversationState.new(uuid4()))

    assert facts.profile is None
    assert facts.bac_specialty is None
    assert facts.denies_bac is True


@pytest.mark.parametrize(
    "message",
    [
        "ena kammelt el prepa",
        "j'ai validé la prépa",
        "prépa déjà réussie",
    ],
)
def test_completed_prepa_is_a_holder_profile(message: str) -> None:
    facts, _ = _extract(message, ConversationState.new(uuid4()))

    assert facts.profile is AcademicProfile.PREPA_HOLDER


def test_completed_prepa_with_continuation_goal_targets_engineering() -> None:
    facts, _ = _extract(
        "ena kammelt el prepa w jey nheb nkammel 9rayti ansahni",
        ConversationState.new(uuid4()),
    )

    assert facts.profile is AcademicProfile.PREPA_HOLDER
    assert facts.target == "ENGINEERING"


@pytest.mark.parametrize(
    "message",
    [
        "j ai deja fait la preinscription",
        "c'est bon amlt preinscrit",
        "3amlt preinscrit chnouma lawra9",
        "la pré-inscription est faite",
    ],
)
def test_completed_pre_registration_is_remembered(message: str) -> None:
    state = ConversationState.new(uuid4())
    facts, negation = _extract(message, state)

    ProfileResolver().apply(state, facts, negation)

    assert facts.pre_registration_completed is True
    assert state.active_state.pre_registration_completed is True


def test_hypothetical_profile_is_isolated_from_the_real_user() -> None:
    state = ConversationState.new(uuid4())
    real_user = state.subjects[ConversationSubject.SELF]
    real_user.profile = AcademicProfile.LICENCE_HOLDER
    real_user.licence_specialty = "INFORMATIQUE"
    real_user.interests = ["SOFTWARE"]

    facts, negation = _extract("si j avais un bac sport, est-ce que la prépa passe ?", state)
    ProfileResolver().apply(state, facts, negation)

    assert state.active_subject is ConversationSubject.HYPOTHETICAL
    assert state.active_state.profile is AcademicProfile.NEW_BAC
    assert state.active_state.bac_specialty == "SPORT"
    assert state.subjects[ConversationSubject.SELF] is real_user
    assert real_user.profile is AcademicProfile.LICENCE_HOLDER
    assert real_user.licence_specialty == "INFORMATIQUE"
    assert real_user.interests == ["SOFTWARE"]


def test_contextual_10_w_9_resolves_the_pending_bac_level() -> None:
    subject = ConversationState.new(uuid4()).active_state
    subject.pending_slot = "BAC_LEVEL"
    subject.last_intents = ["ORIENTATION"]

    result = PendingSlotResolver().resolve("10 w 9", subject)

    assert result.parsed is True
    assert result.previous_intents == ("ORIENTATION",)
    assert subject.bac_average == 10
    assert subject.math_grade == 9
    assert subject.math_comfort == "LOW"
    assert subject.pending_slot is None


def test_bac_specialty_answer_clears_pending_slot_and_keeps_orientation() -> None:
    state = ConversationState.new(uuid4())
    subject = state.active_state
    subject.profile = AcademicProfile.NEW_BAC
    subject.pending_slot = "BAC_SPECIALTY"
    subject.last_intents = ["ORIENTATION"]
    facts, negation = _extract("Économie", state)
    ProfileResolver().apply(state, facts, negation)

    result = PendingSlotResolver().resolve("Économie", subject)

    assert result.parsed is True
    assert result.previous_intents == ("ORIENTATION",)
    assert subject.bac_specialty == "ECONOMIE_GESTION"
    assert subject.pending_slot is None


def test_short_eco_answer_resolves_the_pending_bac_specialty() -> None:
    subject = ConversationState.new(uuid4()).active_state
    subject.profile = AcademicProfile.NEW_BAC
    subject.pending_slot = "BAC_SPECIALTY"
    subject.last_intents = ["ORIENTATION"]

    result = PendingSlotResolver().resolve("Eco", subject)

    assert result.parsed is True
    assert subject.bac_specialty == "ECONOMIE_GESTION"
    assert subject.pending_slot is None


def test_short_science_answer_resolves_the_pending_bac_specialty() -> None:
    subject = ConversationState.new(uuid4()).active_state
    subject.profile = AcademicProfile.NEW_BAC
    subject.pending_slot = "BAC_SPECIALTY"
    subject.last_intents = ["ORIENTATION"]

    result = PendingSlotResolver().resolve("Science", subject)

    assert result.parsed is True
    assert result.previous_intents == ("ORIENTATION",)
    assert subject.bac_specialty == "SCIENCES"
    assert subject.pending_slot is None


def test_bac_letters_is_recognized_without_inventing_a_licence_profile() -> None:
    state = ConversationState.new(uuid4())
    facts, negation = _extract(
        "je suis bac lettres, est-ce que je peux faire une licence industrielle ?",
        state,
    )

    ProfileResolver().apply(state, facts, negation)

    assert facts.profile is AcademicProfile.NEW_BAC
    assert state.active_state.profile is AcademicProfile.NEW_BAC
    assert state.active_state.bac_specialty == "LETTERS"
    assert state.active_state.licence_specialty is None


def test_prompt_facts_use_student_facing_labels_only() -> None:
    state = ConversationState.new(uuid4())
    subject = state.active_state
    subject.profile = AcademicProfile.NEW_BAC
    subject.bac_specialty = "ECONOMIE_GESTION"
    subject.interests = ["DATA_AI"]

    known, forbidden = KnownFactsBuilder().build(subject)

    assert "nouveau bachelier" in known
    assert "Économie et Gestion" in known
    assert "Data et intelligence artificielle" in known
    assert "NEW_BAC" not in known
    assert "ECONOMIE_GESTION" not in known
    assert "code interne" in forbidden


@pytest.mark.parametrize(
    ("message", "scope"),
    [
        ("donne-moi tous les tarifs", ContextScope.ALL),
        ("choufli haja okhra", ContextScope.OTHER),
        ("plus de détails", ContextScope.MORE),
        ("combien coûte la prépa", ContextScope.CURRENT),
    ],
)
def test_contextual_scope_is_deterministic(message: str, scope: ContextScope) -> None:
    assert ContextualModifierDetector().detect(message) is scope


def test_negated_domains_and_offers_become_rejections() -> None:
    detector = NegationDetector()

    domain = detector.detect("je n aime pas l informatique")
    offer = detector.detect("ma3ejbetnich GLID, choufli haja okhra")

    assert domain.has_negation is True
    assert domain.rejected_domains == ("INFORMATIQUE",)
    assert offer.rejected_offers == ("GLID",)
    assert offer.request_alternative is True


def test_negated_interest_is_not_persisted_as_a_positive_preference() -> None:
    state = ConversationState.new(uuid4())
    message = "ma nhebch data ni intelligence artificielle"
    facts, negation = _extract(message, state)

    ProfileResolver().apply(state, facts, negation)

    assert facts.interests == ()
    assert state.active_state.interests == []


def test_licence_info_engineering_goal_is_extracted_without_polluting_specialty() -> None:
    state = ConversationState.new(uuid4())
    facts, negation = _extract(
        "J'ai une licence info et je veux continuer en ingénierie, tu me conseilles quoi ?",
        state,
    )
    ProfileResolver().apply(state, facts, negation)

    assert state.active_state.profile is AcademicProfile.LICENCE_HOLDER
    assert state.active_state.licence_specialty == "INFO"
    assert state.active_state.target == "ENGINEERING"
    assert state.active_state.interests == ["GENERAL_INFO"]
