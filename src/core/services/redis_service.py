import json
from datetime import datetime, timedelta

from dateutil.tz import UTC
from redis.asyncio import Redis

from src.core.config import settings


class RedisService:
    def __init__(self):
        self.client = Redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

    async def set(self, key: str, value: str | int, expire: int | timedelta):
        """Set value in Redis."""
        await self.client.set(key, value, ex=expire)

    async def get(self, key: str) -> str | None:
        """Get value from Redis."""
        return await self.client.get(key)

    async def delete(self, *keys: str):
        """Delete keys from Redis."""
        if keys:
            await self.client.delete(*keys)

    async def increment(self, key: str) -> int:
        """Increment value in Redis."""
        return await self.client.incr(key)

    async def expire(self, key: str, time: int | timedelta):
        """Expire key in Redis."""
        await self.client.expire(key, time)

    async def close(self):
        """Close Redis connection."""
        await self.client.close()

    async def check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """
        Checks the rate limit for the specified key.

        Args:
            key: Redis key (e.g., rate_limit:127.0.0.1:login)
            limit: Maximum number of allowed requests (e.g., 5)
            window: Duration window in seconds (e.g., 60)

        Returns:
            bool: True if the limit has not been exceeded, False if it has been exceeded
        """

        current_count = await self.client.incr(key)

        if current_count == 1:
            await self.client.expire(key, window)

        return current_count <= limit

    async def cache_refresh_token(
        self,
        token_hash: str,
        user_id: str,
        device_id: str | None,
        expires_at: datetime,
    ) -> None:
        """Cache refresh token metadata for fast validation."""
        key = f"refresh_token:{token_hash}"
        value = json.dumps(
            {
                "user_id": user_id,
                "device_id": device_id,
                "expires_at": expires_at.isoformat(),
            }
        )

        ttl = int((expires_at - datetime.now(tz=UTC)).total_seconds())

        if ttl > 0:
            await self.set(key, value, expire=ttl)

    async def get_cached_token(self, token_hash: str) -> dict | None:
        """Get cached token metadata."""
        key = f"refresh_token:{token_hash}"
        value = await self.get(key)

        if value:
            return json.loads(value)
        return None

    async def invalidate_token_cache(self, token_hash: str) -> None:
        """Remove token from cache (on revoke)."""
        key = f"refresh_token:{token_hash}"
        await self.delete(key)


redis_service = RedisService()


async def get_redis_service() -> RedisService:
    return redis_service
