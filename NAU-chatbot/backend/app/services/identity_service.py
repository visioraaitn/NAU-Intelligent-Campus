from __future__ import annotations

import hmac
import secrets
from dataclasses import replace
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.core.security import AuthPrincipal, AuthService, TokenPair
from app.models.sqlalchemy import UserAccount
from app.repositories.identity import UserAccountRepository


class IdentityService:
    def __init__(
        self,
        session: AsyncSession,
        users: UserAccountRepository,
        auth: AuthService,
    ) -> None:
        self.session = session
        self.users = users
        self.auth = auth

    async def signup(self, name: str, email: str, password: str, confirmation: str) -> TokenPair:
        if not hmac.compare_digest(password, confirmation):
            raise ConflictError("Les mots de passe ne correspondent pas.")
        normalized_email = email.strip().casefold()
        if await self.users.email_exists(normalized_email):
            raise ConflictError("Un compte existe déjà avec cette adresse.")
        user = UserAccount(
            name=" ".join(name.split()),
            email=normalized_email,
            password_hash=self.auth.hash_password(password),
            role="USER",
            active=True,
        )
        self.users.add(user)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Un compte existe déjà avec cette adresse.") from exc
        await self.session.refresh(user)
        return await self.auth.issue_user(user)

    async def ensure_chat_principal(self, principal: AuthPrincipal) -> AuthPrincipal:
        if principal.user_id is not None:
            return principal

        account_id = uuid5(NAMESPACE_URL, f"iit-chat-admin:{principal.subject}")
        account = await self.users.get(account_id)
        if account is None:
            account = UserAccount(
                id=account_id,
                name=principal.name,
                email=f"{account_id}@admin-chat.iit.local",
                password_hash=self.auth.hash_password(secrets.token_urlsafe(32)),
                role="ADMIN",
                active=True,
            )
            self.users.add(account)
            try:
                await self.session.commit()
            except IntegrityError:
                await self.session.rollback()
                account = await self.users.get(account_id)
                if account is None:
                    raise
            else:
                await self.session.refresh(account)

        return replace(principal, user_id=account.id, email=account.email)
