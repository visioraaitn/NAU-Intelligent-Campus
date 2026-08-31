from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from redis.asyncio import Redis

from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.domain.conversation.models import ConversationState


class RedisConversationMemory:
    KEY_PREFIX = "iit:chat:session:"
    IDEMPOTENCY_PREFIX = "iit:chat:idempotency:"

    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.ttl = settings.session_ttl_seconds
        self.history_limit = settings.recent_history_limit

    @classmethod
    def key(cls, session_id: UUID) -> str:
        return f"{cls.KEY_PREFIX}{session_id}"

    async def create(self) -> ConversationState:
        for _ in range(3):
            session_id = uuid4()
            state = ConversationState.new(session_id)
            created = await self.redis.set(
                self.key(session_id),
                state.model_dump_json(),
                ex=self.ttl,
                nx=True,
            )
            if created:
                return state
        raise RuntimeError("unable to allocate a unique conversation session")

    async def load(self, session_id: UUID, *, required: bool = True) -> ConversationState | None:
        raw = await self.redis.get(self.key(session_id))
        if raw is None:
            if required:
                raise NotFoundError("conversation", session_id)
            return None
        state = ConversationState.model_validate_json(raw)
        await self.redis.expire(self.key(session_id), self.ttl)
        return state

    async def save(self, state: ConversationState) -> None:
        state.history = state.history[-self.history_limit :]
        state.updated_at = datetime.now(UTC)
        await self.redis.set(
            self.key(state.session_id),
            state.model_dump_json(),
            ex=self.ttl,
        )

    async def reset(self, session_id: UUID) -> bool:
        return bool(await self.redis.delete(self.key(session_id)))

    @classmethod
    def idempotency_key(cls, session_id: UUID, key: str) -> str:
        return f"{cls.IDEMPOTENCY_PREFIX}{session_id}:{key}"

    async def get_idempotent_response(self, session_id: UUID, key: str) -> str | None:
        return await self.redis.get(self.idempotency_key(session_id, key))

    async def store_idempotent_response(
        self,
        session_id: UUID,
        key: str,
        response_json: str,
    ) -> None:
        await self.redis.set(
            self.idempotency_key(session_id, key),
            response_json,
            ex=min(self.ttl, 3_600),
            nx=True,
        )

