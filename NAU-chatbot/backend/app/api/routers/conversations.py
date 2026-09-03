from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import conversation_service, require_chat_user
from app.core.security import AuthPrincipal
from app.models.schemas.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationPage,
    ConversationRead,
    ConversationUpdate,
    MessageRead,
)
from app.services.conversation_service import ConversationService


router = APIRouter(prefix="/conversations", tags=["conversations"])


def _read(entity: object) -> ConversationRead:
    return ConversationRead.model_validate(entity)


@router.get("", response_model=ConversationPage)
async def list_conversations(
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
    principal: AuthPrincipal = Depends(require_chat_user),
    service: ConversationService = Depends(conversation_service),
) -> ConversationPage:
    items, total = await service.list(principal.user_id, limit, offset)  # type: ignore[arg-type]
    return ConversationPage(items=[_read(item) for item in items], total=total, limit=limit, offset=offset)


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    principal: AuthPrincipal = Depends(require_chat_user),
    service: ConversationService = Depends(conversation_service),
) -> ConversationRead:
    return _read(await service.create(principal.user_id, payload.title_source))  # type: ignore[arg-type]


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    principal: AuthPrincipal = Depends(require_chat_user),
    service: ConversationService = Depends(conversation_service),
) -> ConversationDetail:
    entity = await service.get(principal.user_id, conversation_id)  # type: ignore[arg-type]
    return ConversationDetail(
        **_read(entity).model_dump(),
        messages=[MessageRead.model_validate(item) for item in entity.messages],
    )


@router.patch("/{conversation_id}", response_model=ConversationRead)
async def rename_conversation(
    conversation_id: UUID,
    payload: ConversationUpdate,
    principal: AuthPrincipal = Depends(require_chat_user),
    service: ConversationService = Depends(conversation_service),
) -> ConversationRead:
    return _read(await service.rename(principal.user_id, conversation_id, payload.title))  # type: ignore[arg-type]


@router.delete(
    "/{conversation_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(
    conversation_id: UUID,
    principal: AuthPrincipal = Depends(require_chat_user),
    service: ConversationService = Depends(conversation_service),
) -> None:
    await service.delete(principal.user_id, conversation_id)  # type: ignore[arg-type]
