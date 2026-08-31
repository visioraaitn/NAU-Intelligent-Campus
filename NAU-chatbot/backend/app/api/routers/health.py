from __future__ import annotations

import asyncio
from collections.abc import Awaitable

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    chroma_dependency,
    inference_dependency,
    redis_dependency,
)
from app.infrastructure.chroma import AsyncChromaRepository
from app.infrastructure.db import get_session
from app.infrastructure.inference import HttpInferenceClient


router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


async def _check(name: str, operation: Awaitable[object]) -> tuple[str, str]:
    try:
        result = await asyncio.wait_for(operation, timeout=3.0)
        if result is False:
            return name, "unavailable"
        return name, "ready"
    except Exception:
        return name, "unavailable"


@router.get("/health/ready")
async def readiness(
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(redis_dependency),
    chroma: AsyncChromaRepository = Depends(chroma_dependency),
    inference: HttpInferenceClient = Depends(inference_dependency),
) -> JSONResponse:
    results = await asyncio.gather(
        _check("postgresql", session.execute(text("SELECT 1"))),
        _check("redis", redis.ping()),
        _check("chroma", chroma.heartbeat()),
        _check("inference", inference.health()),
    )
    dependencies = dict(results)
    ready = all(value == "ready" for value in dependencies.values())
    return JSONResponse(
        status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ready" if ready else "not_ready", "dependencies": dependencies},
    )
