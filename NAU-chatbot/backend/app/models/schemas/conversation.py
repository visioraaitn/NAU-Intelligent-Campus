from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True, str_strip_whitespace=True)


class ConversationCreate(ConversationSchema):
    title_source: str = Field(min_length=1, max_length=4_000)


class ConversationUpdate(ConversationSchema):
    title: str = Field(min_length=1, max_length=160)


class MessageRead(ConversationSchema):
    id: UUID
    role: Literal["USER", "ASSISTANT"]
    content: str
    created_at: datetime


class ConversationRead(ConversationSchema):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationRead):
    messages: list[MessageRead]


class ConversationPage(ConversationSchema):
    items: list[ConversationRead]
    total: int
    limit: int
    offset: int
