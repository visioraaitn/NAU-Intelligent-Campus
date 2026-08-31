from __future__ import annotations

from redis.asyncio import Redis

from app.core.exceptions import RateLimitError


class RedisRateLimiter:
    """Atomic fixed-window limiter with bounded key cardinality."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def enforce(self, bucket: str, limit: int, window_seconds: int = 60) -> None:
        key = f"iit:rate:{bucket}"
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.ttl(key)
            count, ttl = await pipe.execute()
        if ttl < 0:
            await self.redis.expire(key, window_seconds)
            ttl = window_seconds
        if int(count) > limit:
            raise RateLimitError(max(1, int(ttl)))

