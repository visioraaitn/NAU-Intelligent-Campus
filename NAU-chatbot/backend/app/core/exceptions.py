from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AppError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: object) -> None:
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} introuvable.",
            status_code=404,
            details={"resource": resource, "identifier": str(identifier)},
        )


class ConflictError(AppError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__("CONFLICT", message, 409, details or {})


class AuthenticationError(AppError):
    def __init__(self, message: str = "Authentification requise.") -> None:
        super().__init__("AUTHENTICATION_REQUIRED", message, 401)


class AuthorizationError(AppError):
    def __init__(self, message: str = "Action non autorisée.") -> None:
        super().__init__("FORBIDDEN", message, 403)


class RateLimitError(AppError):
    def __init__(self, retry_after: int) -> None:
        super().__init__(
            "RATE_LIMITED",
            "Trop de requêtes. Réessaie dans un instant.",
            429,
            {"retry_after": retry_after},
        )


class DependencyUnavailableError(AppError):
    def __init__(self, dependency: str) -> None:
        super().__init__(
            "DEPENDENCY_UNAVAILABLE",
            "Un service nécessaire est temporairement indisponible.",
            503,
            {"dependency": dependency},
        )

