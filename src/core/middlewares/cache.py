"""Response caching middleware using Redis.

This module provides a decorator for caching API responses in Redis.
Useful for read-heavy endpoints that don't change frequently.
"""

import functools
import hashlib
import json
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from src.core.logging import get_logger
from src.core.services.redis_service import RedisService

logger = get_logger(__name__)


def cache_response(expire: int = 300, key_prefix: str | None = None):
    """Decorator to cache API response in Redis.

    Args:
        expire: Cache expiration time in seconds (default: 300 = 5 minutes)
        key_prefix: Optional prefix for cache key (default: uses function name)

    Usage:
        @router.get("/countries")
        @cache_response(expire=3600)  # Cache for 1 hour
        async def get_countries():
            return {"countries": [...]}

    Cache keys are generated from:
    - URL path
    - Query parameters
    - User ID (if authenticated)

    Notes:
    - Only caches GET requests
    - Only caches 200 OK responses
    - Cache is bypassed if X-No-Cache header is present
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Extract request from kwargs
            request: Request | None = kwargs.get("request")

            # Only cache GET requests
            if not request or request.method != "GET":
                return await func(*args, **kwargs)

            # Check if caching should be bypassed
            if request.headers.get("X-No-Cache"):
                logger.debug("Cache bypassed due to X-No-Cache header")
                return await func(*args, **kwargs)

            # Get Redis service (passed via dependency injection or from kwargs)
            redis: RedisService | None = kwargs.get("redis")
            if not redis:
                # If no redis available, just execute function
                logger.debug("No Redis service available, skipping cache")
                return await func(*args, **kwargs)

            # Generate cache key
            prefix = key_prefix or func.__name__

            # Build cache key from request details
            cache_key_parts = [
                prefix,
                request.url.path,
                str(sorted(request.query_params.items())),
            ]

            # Add user ID if authenticated (from request state set by auth middleware)
            if hasattr(request.state, "user"):
                cache_key_parts.append(str(request.state.user.id))

            # Hash the key parts to create a consistent cache key
            key_string = "|".join(cache_key_parts)
            cache_key = f"cache:{hashlib.md5(key_string.encode()).hexdigest()}"

            # Try to get from cache
            try:
                cached = await redis.get(cache_key)
                if cached:
                    logger.debug(f"Cache HIT: {cache_key}")
                    # Parse cached response
                    cached_data = json.loads(cached)
                    return JSONResponse(
                        content=cached_data["content"],
                        status_code=cached_data["status_code"],
                        headers={"X-Cache": "HIT"},
                    )
            except Exception as e:
                logger.warning(f"Cache read error: {e}")

            logger.debug(f"Cache MISS: {cache_key}")

            # Execute function
            result = await func(*args, **kwargs)

            # Cache the response if it's successful
            if isinstance(result, (dict, list)):
                # Direct dict/list response
                try:
                    cache_data = {
                        "content": result,
                        "status_code": 200,
                    }
                    await redis.set(cache_key, json.dumps(cache_data), expire=expire)
                    logger.debug(f"Cached response for {expire}s: {cache_key}")
                except Exception as e:
                    logger.warning(f"Cache write error: {e}")

            elif isinstance(result, Response) and result.status_code == 200:
                # JSONResponse or other Response object
                try:
                    cache_data = {
                        "content": json.loads(result.body),
                        "status_code": result.status_code,
                    }
                    await redis.set(cache_key, json.dumps(cache_data), expire=expire)
                    logger.debug(f"Cached response for {expire}s: {cache_key}")
                except Exception as e:
                    logger.warning(f"Cache write error: {e}")

            return result

        return wrapper

    return decorator


async def clear_cache_by_prefix(redis: RedisService, prefix: str) -> int:
    """Clear all cache entries matching a prefix.

    Args:
        redis: Redis service instance
        prefix: Cache key prefix to match

    Returns:
        Number of keys deleted

    Usage:
        # Clear all country cache entries
        await clear_cache_by_prefix(redis, "cache:get_countries")
    """
    try:
        # Get all keys matching the pattern
        pattern = f"cache:*{prefix}*"
        keys = []

        # Redis SCAN command for safer iteration
        cursor = 0
        while True:
            cursor, batch = await redis.client.scan(cursor, match=pattern, count=100)
            keys.extend(batch)
            if cursor == 0:
                break

        # Delete all matching keys
        if keys:
            deleted = await redis.client.delete(*keys)
            logger.info(f"Cleared {deleted} cache entries for prefix: {prefix}")
            return deleted

        return 0

    except Exception as e:
        logger.error(f"Error clearing cache by prefix {prefix}: {e}")
        return 0
