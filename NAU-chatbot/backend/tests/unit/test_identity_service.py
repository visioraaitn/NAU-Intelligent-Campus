from __future__ import annotations

from uuid import UUID

from app.core.security import AuthPrincipal
from app.services.identity_service import IdentityService


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.refreshes = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def refresh(self, _entity: object) -> None:
        self.refreshes += 1


class FakeUsers:
    def __init__(self) -> None:
        self.account = None

    async def get(self, user_id):
        if self.account is not None and self.account.id == user_id:
            return self.account
        return None

    def add(self, account) -> None:
        self.account = account


class FakeAuth:
    @staticmethod
    def hash_password(_password: str) -> str:
        return "unusable-admin-chat-password"


async def test_admin_gets_a_stable_persistent_chat_identity() -> None:
    session = FakeSession()
    users = FakeUsers()
    service = IdentityService(session, users, FakeAuth())  # type: ignore[arg-type]
    principal = AuthPrincipal(
        subject="admin",
        role="ADMIN",
        name="Administrateur",
    )

    first = await service.ensure_chat_principal(principal)
    second = await service.ensure_chat_principal(principal)

    assert first.user_id is not None
    assert first.user_id == second.user_id
    assert first.email == second.email
    assert users.account.role == "ADMIN"
    assert session.commits == 1
    assert session.refreshes == 1
    assert session.rollbacks == 0


async def test_existing_user_chat_identity_is_unchanged() -> None:
    session = FakeSession()
    service = IdentityService(session, FakeUsers(), FakeAuth())  # type: ignore[arg-type]
    principal = AuthPrincipal(
        subject="8bb8897f-b893-43de-9b41-f1a113832d10",
        role="USER",
        name="Utilisateur",
        user_id=UUID("8bb8897f-b893-43de-9b41-f1a113832d10"),
    )

    assert await service.ensure_chat_principal(principal) is principal
    assert session.commits == 0
