from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AcademicProfile(str, Enum):
    UNKNOWN = "UNKNOWN"
    NEW_BAC = "NEW_BAC"
    PREPA_STUDENT = "PREPA_STUDENT"
    PREPA_HOLDER = "PREPA_HOLDER"
    LICENCE_STUDENT = "LICENCE_STUDENT"
    LICENCE_HOLDER = "LICENCE_HOLDER"
    MASTER_HOLDER = "MASTER_HOLDER"

    @property
    def rank(self) -> int:
        return {
            AcademicProfile.UNKNOWN: 0,
            AcademicProfile.NEW_BAC: 1,
            AcademicProfile.PREPA_STUDENT: 2,
            AcademicProfile.PREPA_HOLDER: 2,
            AcademicProfile.LICENCE_STUDENT: 3,
            AcademicProfile.LICENCE_HOLDER: 3,
            AcademicProfile.MASTER_HOLDER: 4,
        }[self]


class ConversationSubject(str, Enum):
    SELF = "SELF"
    FRIEND = "FRIEND"
    FAMILY = "FAMILY"
    HYPOTHETICAL = "HYPOTHETICAL"


class ConversionStage(str, Enum):
    DISCOVERY = "DISCOVERY"
    QUALIFICATION = "QUALIFICATION"
    RECOMMENDATION = "RECOMMENDATION"
    EXPLORATION = "EXPLORATION"
    OBJECTION_HANDLING = "OBJECTION_HANDLING"
    INTEREST = "INTEREST"
    PRE_REGISTRATION = "PRE_REGISTRATION"


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8_000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SubjectState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: AcademicProfile = AcademicProfile.UNKNOWN
    licence_specialty: str | None = None
    bac_specialty: str | None = None
    bac_average: float | None = Field(default=None, ge=0, le=20)
    math_comfort: str | None = None
    math_grade: float | None = Field(default=None, ge=0, le=20)
    prepa_type: str | None = None
    target: str | None = None
    interests: list[str] = Field(default_factory=list, max_length=32)
    difficulty_preferences: list[str] = Field(default_factory=list, max_length=16)
    recommended_offer: str | None = None
    recommended_specialisation: str | None = None
    pending_slot: str | None = None
    pending_action: str | None = None
    asked_slots: dict[str, int] = Field(default_factory=dict)
    rejected_slots: list[str] = Field(default_factory=list, max_length=32)
    rejected_offers: list[str] = Field(default_factory=list, max_length=64)
    rejected_domains: list[str] = Field(default_factory=list, max_length=32)
    last_question_asked: str | None = None
    last_intents: list[str] = Field(default_factory=list, max_length=32)
    last_scope: str = "CURRENT"
    last_dialogue_act: str | None = None
    last_user_message: str = ""
    last_answer_focus: list[str] = Field(default_factory=list, max_length=32)
    covered_topics: list[str] = Field(default_factory=list, max_length=64)
    detail_level: int = Field(default=0, ge=0, le=5)
    finishing_current_degree: bool = False
    pre_registration_completed: bool = False
    profile_intro_done: bool = False
    offer_intro_done: bool = False
    last_answer_text: str = ""
    last_cta_turn: int = -99
    cta_count: int = Field(default=0, ge=0)
    last_recommendation_turn: int = -99
    conversion_stage: ConversionStage = ConversionStage.DISCOVERY


def _subject_map() -> dict[ConversationSubject, SubjectState]:
    return {subject: SubjectState() for subject in ConversationSubject}


class ConversationState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    started: bool = False
    turn_count: int = Field(default=0, ge=0)
    active_subject: ConversationSubject = ConversationSubject.SELF
    subjects: dict[ConversationSubject, SubjectState] = Field(default_factory=_subject_map)
    history: list[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def new(cls, session_id: UUID) -> ConversationState:
        return cls(session_id=session_id)

    @property
    def active_state(self) -> SubjectState:
        return self.subjects[self.active_subject]

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)
