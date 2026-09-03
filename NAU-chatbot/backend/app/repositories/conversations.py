from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.sqlalchemy import Conversation, ConversationMessage


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_owned(self, user_id: UUID, limit: int, offset: int) -> tuple[list[Conversation], int]:
        condition = Conversation.user_id == user_id
        total = int((await self.session.scalar(select(func.count()).select_from(Conversation).where(condition))) or 0)
        rows = await self.session.scalars(
            select(Conversation)
            .where(condition)
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(rows.all()), total

    async def get_owned(self, conversation_id: UUID, user_id: UUID, *, with_messages: bool = False) -> Conversation | None:
        query = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        if with_messages:
            query = query.options(selectinload(Conversation.messages))
        return await self.session.scalar(query)

    async def get(self, conversation_id: UUID) -> Conversation | None:
        return await self.session.get(Conversation, conversation_id)

    def add(self, entity: Conversation | ConversationMessage) -> None:
        self.session.add(entity)

    async def message_by_request(self, conversation_id: UUID, role: str, request_key: str) -> ConversationMessage | None:
        return await self.session.scalar(
            select(ConversationMessage).where(
                ConversationMessage.conversation_id == conversation_id,
                ConversationMessage.role == role,
                ConversationMessage.request_key == request_key,
            )
        )

    async def delete_owned(self, conversation_id: UUID, user_id: UUID) -> bool:
        result = await self.session.execute(
            delete(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return bool(result.rowcount)
