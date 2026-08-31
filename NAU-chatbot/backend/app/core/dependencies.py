from __future__ import annotations

import hashlib

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError
from app.core.security import AuthService
from app.infrastructure.chroma import AsyncChromaRepository
from app.infrastructure.db import get_session
from app.infrastructure.inference import HttpInferenceClient
from app.infrastructure.redis import get_redis
from app.infrastructure.redis.event_publisher import RedisAcademicEventPublisher
from app.repositories.academic import (
    FormationRepository,
    OrientationRuleRepository,
)
from app.services.academic.catalog_service import AcademicCatalogService
from app.services.admin.academic_service import AcademicAdminService
from app.services.admin.rag_service import RagAdminService
from app.services.dialogue.orchestrator import ChatOrchestrator
from app.services.eligibility import EligibilityService
from app.services.memory import RedisConversationMemory, SessionLockManager
from app.services.memory.rate_limiter import RedisRateLimiter
from app.services.rag.indexer import RagIndexer
from app.services.rag.retriever import RagRetriever
from app.services.rag.status_store import RagStatusStore
from app.services.recommendation import RecommendationService


bearer = HTTPBearer(auto_error=False)


def settings_dependency() -> Settings:
    return get_settings()


def redis_dependency() -> Redis:
    return get_redis()


def inference_dependency(request: Request) -> HttpInferenceClient:
    return request.app.state.inference


def chroma_dependency(request: Request) -> AsyncChromaRepository:
    return request.app.state.chroma


def auth_service(request: Request) -> AuthService:
    return request.app.state.auth


async def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    auth: AuthService = Depends(auth_service),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError()
    claims = auth.decode(credentials.credentials, expected_type="access")
    return str(claims["sub"])


def rate_limiter(redis: Redis = Depends(redis_dependency)) -> RedisRateLimiter:
    return RedisRateLimiter(redis)


async def enforce_admin_rate_limit(
    request: Request,
    limiter: RedisRateLimiter = Depends(rate_limiter),
    settings: Settings = Depends(settings_dependency),
) -> None:
    """Apply a separate bounded budget to every protected admin request."""

    await limiter.enforce(
        client_bucket(request, "admin", settings),
        settings.admin_rate_limit_per_minute,
    )


def admin_service(
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(redis_dependency),
    settings: Settings = Depends(settings_dependency),
) -> AcademicAdminService:
    return AcademicAdminService(
        session,
        RedisAcademicEventPublisher(redis, settings),
    )


def rag_admin_service(
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(redis_dependency),
    settings: Settings = Depends(settings_dependency),
) -> RagAdminService:
    return RagAdminService(
        FormationRepository(session),
        RedisAcademicEventPublisher(redis, settings),
        RagStatusStore(redis, settings),
    )


def memory_service(
    redis: Redis = Depends(redis_dependency),
    settings: Settings = Depends(settings_dependency),
) -> RedisConversationMemory:
    return RedisConversationMemory(redis, settings)


def lock_service(
    redis: Redis = Depends(redis_dependency),
    settings: Settings = Depends(settings_dependency),
) -> SessionLockManager:
    return SessionLockManager(redis, settings)


def orchestrator(
    session: AsyncSession = Depends(get_session),
    inference: HttpInferenceClient = Depends(inference_dependency),
    chroma: AsyncChromaRepository = Depends(chroma_dependency),
) -> ChatOrchestrator:
    catalogue = AcademicCatalogService(session)
    eligibility = EligibilityService(OrientationRuleRepository(session))
    return ChatOrchestrator(
        catalogue=catalogue,
        eligibility=eligibility,
        recommendation=RecommendationService(catalogue, eligibility),
        rag=RagRetriever(chroma, inference, inference),
        llm=inference,
    )


def client_bucket(request: Request, scope: str, settings: Settings) -> str:
    host = request.client.host if request.client else "unknown"
    digest = hashlib.sha256(
        (settings.app_secret_key.get_secret_value() + ":" + host).encode()
    ).hexdigest()[:24]
    return f"{scope}:{digest}"
