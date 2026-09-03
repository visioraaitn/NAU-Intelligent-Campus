from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sqlalchemy import UserAccount


class UserAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> UserAccount | None:
        return await self.session.scalar(
            select(UserAccount).where(UserAccount.email == email)
        )

    async def get(self, user_id: UUID) -> UserAccount | None:
        return await self.session.get(UserAccount, user_id)

    def add(self, user: UserAccount) -> None:
        self.session.add(user)

    async def email_exists(self, email: str) -> bool:
        return bool(
            await self.session.scalar(
                select(func.count(UserAccount.id)).where(UserAccount.email == email)
            )
        )
