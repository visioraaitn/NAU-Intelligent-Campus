from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    session_id: UUID
    message: str = Field(min_length=1, max_length=4_000)


class ChatResponse(BaseModel):
    session_id: UUID
    answer: str


class ChatSessionResponse(BaseModel):
    session_id: UUID
    expires_in: int
