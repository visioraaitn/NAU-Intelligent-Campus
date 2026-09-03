from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.conversation.models import ChatMessage, ConversationState
from app.models.schemas.chat import ChatResponse
from app.models.sqlalchemy import Conversation, ConversationMessage
from app.repositories.conversations import ConversationRepository
from app.services.dialogue.chat_service import ChatService
from app.services.memory import RedisConversationMemory


UNTITLED_CONVERSATION = "Nouvelle conversation"


class ConversationService:
    def __init__(
        self,
        session: AsyncSession,
        repository: ConversationRepository,
        memory: RedisConversationMemory,
    ) -> None:
        self.session = session
        self.repository = repository
        self.memory = memory

    async def list(self, user_id: UUID, limit: int, offset: int) -> tuple[list[Conversation], int]:
        return await self.repository.list_owned(user_id, limit, offset)

    async def create(self, user_id: UUID, title_source: str) -> Conversation:
        state = await self.memory.create()
        conversation = Conversation(
            id=state.session_id,
            user_id=user_id,
            title=_conversation_title(title_source),
        )
        self.repository.add(conversation)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            await self.memory.reset(state.session_id)
            raise
        await self.session.refresh(conversation)
        return conversation

    async def get(self, user_id: UUID, conversation_id: UUID) -> Conversation:
        conversation = await self.repository.get_owned(
            conversation_id,
            user_id,
            with_messages=True,
        )
        if conversation is None:
            raise NotFoundError("conversation", conversation_id)
        if await self.memory.load(conversation_id, required=False) is None:
            state = ConversationState.new(conversation_id)
            state.history = [
                ChatMessage(role=item.role.lower(), content=item.content)
                for item in conversation.messages[-self.memory.history_limit :]
            ]
            state.started = bool(state.history)
            state.turn_count = sum(item.role == "USER" for item in conversation.messages)
            await self.memory.save(state)
        return conversation

    async def rename(self, user_id: UUID, conversation_id: UUID, title: str) -> Conversation:
        conversation = await self.repository.get_owned(conversation_id, user_id)
        if conversation is None:
            raise NotFoundError("conversation", conversation_id)
        conversation.title = " ".join(title.split())
        conversation.updated_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def delete(self, user_id: UUID, conversation_id: UUID) -> None:
        if not await self.repository.delete_owned(conversation_id, user_id):
            raise NotFoundError("conversation", conversation_id)
        await self.memory.reset(conversation_id)
        await self.session.commit()


class PersistentChatService:
    def __init__(
        self,
        session: AsyncSession,
        repository: ConversationRepository,
        memory: RedisConversationMemory,
        chat: ChatService,
    ) -> None:
        self.session = session
        self.repository = repository
        self.memory = memory
        self.chat = chat

    async def respond(
        self,
        user_id: UUID,
        session_id: UUID,
        message: str,
        *,
        idempotency_key: str | None,
    ) -> ChatResponse:
        conversation = await self.repository.get(session_id)
        if conversation is not None and conversation.user_id != user_id:
            raise NotFoundError("conversation", session_id)
        if conversation is None:
            if await self.memory.load(session_id, required=False) is None:
                raise NotFoundError("conversation", session_id)
            conversation = Conversation(
                id=session_id,
                user_id=user_id,
                title=_conversation_title(message),
            )
            self.repository.add(conversation)

        if conversation.title == UNTITLED_CONVERSATION:
            conversation.title = _conversation_title(message)

        if idempotency_key:
            assistant = await self.repository.message_by_request(
                session_id,
                "ASSISTANT",
                idempotency_key,
            )
            if assistant is not None:
                return ChatResponse(session_id=session_id, answer=assistant.content)
            existing_user = await self.repository.message_by_request(
                session_id,
                "USER",
                idempotency_key,
            )
        else:
            existing_user = None

        if existing_user is None:
            self.repository.add(
                ConversationMessage(
                    conversation_id=session_id,
                    role="USER",
                    content=message,
                    request_key=idempotency_key,
                )
            )
            conversation.updated_at = datetime.now(UTC)
            await self.session.commit()

        response = await self.chat.respond(
            session_id,
            message,
            idempotency_key=idempotency_key,
        )
        self.repository.add(
            ConversationMessage(
                conversation_id=session_id,
                role="ASSISTANT",
                content=response.answer,
                request_key=idempotency_key,
            )
        )
        conversation.updated_at = datetime.now(UTC)
        await self.session.commit()
        return response


def _conversation_title(message: str) -> str:
    title = re.sub(r"\s+", " ", message).strip()
    if len(title) <= 80:
        return title
    return title[:77].rstrip(" ,.;:-") + "…"
