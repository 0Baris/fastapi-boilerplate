from fastapi import Depends, HTTPException, Request

from src.core.services.redis_service import RedisService, get_redis_service


class RateLimiter:
    """
    IP-based rate limiter dependency for FastAPI routes.

    Usage:
        @router.get("/endpoint", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
        async def my_endpoint():
            ...

    Or use predefined limits:
        @router.get("/endpoint", dependencies=[Depends(rate_limit_strict)])
        @router.post("/auth/login", dependencies=[Depends(rate_limit_auth)])
    """

    def __init__(self, times: int, seconds: int):
        self.times: int = times
        self.seconds: int = seconds

    async def __call__(self, request: Request, redis: RedisService = Depends(get_redis_service)):
        """FastAPI dependency to rate limit requests by IP address."""
        client_ip: str = request.client.host  # ty:ignore[possibly-missing-attribute]
        path: str = request.url.path
        key = f"rate_limit:ip:{client_ip}:{path}"

        allowed: bool = await redis.check_rate_limit(key, self.times, self.seconds)

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Please wait {self.seconds} seconds.",
                headers={"Retry-After": str(self.seconds)},
            )


class UserRateLimiter:
    """
    User-based rate limiter for authenticated endpoints.

    Limits are applied per user ID instead of IP address, providing more accurate
    rate limiting for authenticated users.

    Usage:
        @router.get(
            "/endpoint",
            dependencies=[Depends(get_current_user), Depends(UserRateLimiter(times=100, seconds=60))]
        )
        async def my_endpoint(user: User = Depends(get_current_user)):
            ...
    """

    def __init__(self, times: int, seconds: int):
        self.times: int = times
        self.seconds: int = seconds

    async def __call__(self, request: Request, redis: RedisService = Depends(get_redis_service)):
        """FastAPI dependency to rate limit requests by user ID."""
        # Get user ID from request state (set by auth dependency)
        user_id: str | None = getattr(request.state, "user_id", None)

        if not user_id:
            # Fallback to IP-based if user is not authenticated
            client_ip: str = request.client.host  # ty:ignore[possibly-missing-attribute]
            key = f"rate_limit:ip:{client_ip}:{request.url.path}"
        else:
            key = f"rate_limit:user:{user_id}:{request.url.path}"

        allowed: bool = await redis.check_rate_limit(key, self.times, self.seconds)

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Please wait {self.seconds} seconds.",
                headers={"Retry-After": str(self.seconds)},
            )


# Predefined rate limit configurations for different use cases

# Authentication endpoints (prevent brute force)
rate_limit_auth = RateLimiter(times=5, seconds=300)  # 5 attempts per 5 minutes

# Password reset/forgot password (prevent abuse)
rate_limit_password_reset = RateLimiter(times=3, seconds=3600)  # 3 attempts per hour

# Email verification/resend code
rate_limit_email_verification = RateLimiter(times=5, seconds=3600)  # 5 attempts per hour

# Registration endpoint
rate_limit_registration = RateLimiter(times=3, seconds=3600)  # 3 registrations per hour per IP

# Strict limits for sensitive operations
rate_limit_strict = RateLimiter(times=10, seconds=60)  # 10 requests per minute

# Moderate limits for regular API calls
rate_limit_moderate = RateLimiter(times=60, seconds=60)  # 60 requests per minute

# Relaxed limits for read-only operations
rate_limit_relaxed = RateLimiter(times=200, seconds=60)  # 200 requests per minute

# Public endpoints (very relaxed)
rate_limit_public = RateLimiter(times=1000, seconds=3600)  # 1000 requests per hour

# User-specific rate limits (for authenticated users)
rate_limit_user_moderate = UserRateLimiter(times=100, seconds=60)  # 100 requests per minute per user
rate_limit_user_high = UserRateLimiter(times=500, seconds=60)  # 500 requests per minute per user
