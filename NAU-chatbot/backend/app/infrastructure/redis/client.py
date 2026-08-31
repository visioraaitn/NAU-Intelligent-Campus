from __future__ import annotations

from functools import lru_cache

from redis.asyncio import Redis

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_redis() -> Redis:
    return Redis.from_url(
        get_settings().redis_url.get_secret_value(),
        encoding="utf-8",
        decode_responses=True,
        health_check_interval=30,
    )


async def close_redis() -> None:
    if get_redis.cache_info().currsize:
        await get_redis().aclose()
    get_redis.cache_clear()

