from __future__ import annotations

from uuid import UUID

from app.core.exceptions import NotFoundError
from app.models.schemas.chat import ChatResponse
from app.services.dialogue.orchestrator import ChatOrchestrator
from app.services.memory import RedisConversationMemory, SessionLockManager


class ChatService:
    def __init__(
        self,
        memory: RedisConversationMemory,
        locks: SessionLockManager,
        orchestrator: ChatOrchestrator,
    ) -> None:
        self.memory = memory
        self.locks = locks
        self.orchestrator = orchestrator

    async def respond(
        self,
        session_id: UUID,
        message: str,
        *,
        idempotency_key: str | None = None,
    ) -> ChatResponse:
        if idempotency_key:
            cached = await self.memory.get_idempotent_response(session_id, idempotency_key)
            if cached:
                return ChatResponse.model_validate_json(cached)
        async with self.locks.lock(session_id):
            if idempotency_key:
                cached = await self.memory.get_idempotent_response(session_id, idempotency_key)
                if cached:
                    return ChatResponse.model_validate_json(cached)
            state = await self.memory.load(session_id)
            if state is None:  # Defensive for alternative memory implementations.
                raise NotFoundError("conversation", session_id)
            result = await self.orchestrator.process(message, state)
            await self.memory.save(result.state)
            response = ChatResponse(session_id=session_id, answer=result.answer)
            if idempotency_key:
                await self.memory.store_idempotent_response(
                    session_id,
                    idempotency_key,
                    response.model_dump_json(),
                )
            return response
