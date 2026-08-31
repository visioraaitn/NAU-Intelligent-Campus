from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class InferenceSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


BoundedText = Annotated[str, Field(min_length=1, max_length=8_000)]


class Message(InferenceSchema):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=32_000)


class GenerateRequest(InferenceSchema):
    role: Literal["esprit", "final"]
    messages: list[Message] = Field(min_length=1, max_length=16)
    max_new_tokens: int = Field(default=280, ge=1, le=1_024)


class GenerateResponse(InferenceSchema):
    text: str


class EmbedRequest(InferenceSchema):
    texts: list[BoundedText] = Field(min_length=1, max_length=128)
    query: bool = False


class EmbedResponse(InferenceSchema):
    embeddings: list[list[float]]


class RerankRequest(InferenceSchema):
    query: str = Field(min_length=1, max_length=8_000)
    documents: list[BoundedText] = Field(min_length=1, max_length=128)


class RerankResponse(InferenceSchema):
    scores: list[float]
