from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import NotFoundError
from app.models.schemas.chat import ChatResponse
from app.models.sqlalchemy import Conversation, ConversationMessage
from app.services.conversation_service import ConversationService, PersistentChatService


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None

    async def refresh(self, entity) -> None:
        now = datetime.now(UTC)
        entity.created_at = getattr(entity, "created_at", None) or now
        entity.updated_at = getattr(entity, "updated_at", None) or now


class FakeConversationRepository:
    def __init__(self) -> None:
        self.conversations: dict[UUID, Conversation] = {}
        self.messages: list[ConversationMessage] = []

    async def list_owned(self, user_id: UUID, limit: int, offset: int):
        owned = [item for item in self.conversations.values() if item.user_id == user_id]
        return owned[offset : offset + limit], len(owned)

    async def get_owned(self, conversation_id: UUID, user_id: UUID, *, with_messages: bool = False):
        conversation = self.conversations.get(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            return None
        if with_messages:
            conversation.messages = [
                item for item in self.messages if item.conversation_id == conversation_id
            ]
        return conversation

    async def get(self, conversation_id: UUID):
        return self.conversations.get(conversation_id)

    def add(self, entity) -> None:
        if isinstance(entity, Conversation):
            self.conversations[entity.id] = entity
        else:
            entity.id = getattr(entity, "id", None) or uuid4()
            entity.created_at = getattr(entity, "created_at", None) or datetime.now(UTC)
            self.messages.append(entity)

    async def message_by_request(self, conversation_id: UUID, role: str, request_key: str):
        return next(
            (
                item
                for item in self.messages
                if item.conversation_id == conversation_id
                and item.role == role
                and item.request_key == request_key
            ),
            None,
        )

    async def delete_owned(self, conversation_id: UUID, user_id: UUID) -> bool:
        conversation = self.conversations.get(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            return False
        del self.conversations[conversation_id]
        self.messages = [item for item in self.messages if item.conversation_id != conversation_id]
        return True


class FakeMemory:
    history_limit = 20

    def __init__(self) -> None:
        self.states = {}

    async def create(self):
        state = SimpleNamespace(session_id=uuid4())
        self.states[state.session_id] = state
        return state

    async def load(self, session_id: UUID, *, required: bool = True):
        del required
        return self.states.get(session_id)

    async def save(self, state) -> None:
        self.states[state.session_id] = state

    async def reset(self, session_id: UUID) -> bool:
        return self.states.pop(session_id, None) is not None


class FakeChatService:
    def __init__(self) -> None:
        self.calls = 0

    async def respond(self, session_id: UUID, message: str, *, idempotency_key: str | None):
        self.calls += 1
        return ChatResponse(session_id=session_id, answer=f"Réponse à {message}")


def existing_conversation(repository: FakeConversationRepository, user_id: UUID) -> Conversation:
    now = datetime.now(UTC)
    conversation = Conversation(
        id=uuid4(),
        user_id=user_id,
        title="Question IIT",
        created_at=now,
        updated_at=now,
    )
    repository.add(conversation)
    return conversation


async def test_conversation_operations_are_scoped_to_owner() -> None:
    owner_id = uuid4()
    stranger_id = uuid4()
    repository = FakeConversationRepository()
    conversation = existing_conversation(repository, owner_id)
    service = ConversationService(FakeSession(), repository, FakeMemory())

    with pytest.raises(NotFoundError):
        await service.get(stranger_id, conversation.id)
    with pytest.raises(NotFoundError):
        await service.rename(stranger_id, conversation.id, "Titre volé")
    with pytest.raises(NotFoundError):
        await service.delete(stranger_id, conversation.id)

    assert repository.conversations[conversation.id].title == "Question IIT"


async def test_chat_persists_one_user_and_one_assistant_message_per_request() -> None:
    owner_id = uuid4()
    repository = FakeConversationRepository()
    conversation = existing_conversation(repository, owner_id)
    chat = FakeChatService()
    service = PersistentChatService(FakeSession(), repository, FakeMemory(), chat)

    first = await service.respond(
        owner_id,
        conversation.id,
        "Quels sont les frais ?",
        idempotency_key="request-1234",
    )
    second = await service.respond(
        owner_id,
        conversation.id,
        "Quels sont les frais ?",
        idempotency_key="request-1234",
    )

    assert first.answer == second.answer
    assert [item.role for item in repository.messages] == ["USER", "ASSISTANT"]
    assert chat.calls == 1


async def test_chat_rejects_another_users_conversation() -> None:
    owner_id = uuid4()
    repository = FakeConversationRepository()
    conversation = existing_conversation(repository, owner_id)
    chat = FakeChatService()
    service = PersistentChatService(FakeSession(), repository, FakeMemory(), chat)

    with pytest.raises(NotFoundError):
        await service.respond(
            uuid4(),
            conversation.id,
            "Montre-moi cette conversation",
            idempotency_key="request-5678",
        )

    assert repository.messages == []
    assert chat.calls == 0
