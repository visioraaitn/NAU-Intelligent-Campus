from __future__ import annotations

import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuthSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginRequest(AuthSchema):
    username: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class SignupRequest(AuthSchema):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=256)
    password_confirmation: str = Field(min_length=8, max_length=256)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.casefold()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized):
            raise ValueError("Adresse email invalide.")
        return normalized


class AuthUserResponse(AuthSchema):
    id: UUID | None = None
    name: str
    email: str | None = None
    role: Literal["USER", "ADMIN"]


class TokenResponse(AuthSchema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    csrf_token: str
    user: AuthUserResponse


class LogoutResponse(AuthSchema):
    logged_out: bool = True
