from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status

from app.core.config import Settings
from app.core.dependencies import (
    client_bucket,
    lock_service,
    memory_service,
    orchestrator,
    rate_limiter,
    settings_dependency,
)
from app.models.schemas.chat import ChatRequest, ChatResponse, ChatSessionResponse
from app.services.dialogue.chat_service import ChatService
from app.services.dialogue.orchestrator import ChatOrchestrator
from app.services.memory import RedisConversationMemory, SessionLockManager
from app.services.memory.rate_limiter import RedisRateLimiter


router = APIRouter(prefix="/chat", tags=["chat"])
IdempotencyKey = Annotated[
    str | None,
    Header(alias="Idempotency-Key", min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$"),
]


@router.post("/session", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: Request,
    memory: RedisConversationMemory = Depends(memory_service),
    limiter: RedisRateLimiter = Depends(rate_limiter),
    settings: Settings = Depends(settings_dependency),
) -> ChatSessionResponse:
    await limiter.enforce(
        client_bucket(request, "chat-session", settings),
        settings.chat_rate_limit_per_minute,
    )
    state = await memory.create()
    return ChatSessionResponse(session_id=state.session_id, expires_in=settings.session_ttl_seconds)


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    idempotency_key: IdempotencyKey = None,
    memory: RedisConversationMemory = Depends(memory_service),
    locks: SessionLockManager = Depends(lock_service),
    dialogue: ChatOrchestrator = Depends(orchestrator),
    limiter: RedisRateLimiter = Depends(rate_limiter),
    settings: Settings = Depends(settings_dependency),
) -> ChatResponse:
    await limiter.enforce(
        client_bucket(request, "chat", settings),
        settings.chat_rate_limit_per_minute,
    )
    return await ChatService(memory, locks, dialogue).respond(
        payload.session_id,
        payload.message,
        idempotency_key=idempotency_key,
    )


@router.delete(
    "/session/{session_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_session(
    session_id: UUID,
    memory: RedisConversationMemory = Depends(memory_service),
) -> None:
    await memory.reset(session_id)
