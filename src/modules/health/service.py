import time
from datetime import UTC, datetime

from google.cloud import storage
from redis.asyncio import Redis
from sqlalchemy import text

from src.core.config import settings
from src.core.database import AsyncSessionLocal
from src.core.logging import get_logger
from src.modules.health.schemas import HealthCheckResponse, ServiceStatus

logger = get_logger(__name__)


class HealthCheckService:
    """Service for checking health of all system components."""

    async def check_database(self) -> ServiceStatus:
        """Check PostgreSQL database connectivity."""
        start = time.time()
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(text("SELECT 1"))
                result.scalar()
            response_time = (time.time() - start) * 1000
            return ServiceStatus(
                name="database",
                status="healthy",
                message="PostgreSQL connection successful",
                response_time_ms=round(response_time, 2),
            )
        except Exception as e:
            response_time = (time.time() - start) * 1000
            logger.error(f"Database health check failed: {e}")
            return ServiceStatus(
                name="database",
                status="unhealthy",
                message=f"Database connection failed: {e!s}",
                response_time_ms=round(response_time, 2),
            )

    async def check_redis(self) -> ServiceStatus:
        """Check Redis connectivity."""
        start = time.time()
        try:
            redis_client = Redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            await redis_client.ping()
            await redis_client.aclose()
            response_time = (time.time() - start) * 1000
            return ServiceStatus(
                name="redis",
                status="healthy",
                message="Redis connection successful",
                response_time_ms=round(response_time, 2),
            )
        except Exception as e:
            response_time = (time.time() - start) * 1000
            logger.error(f"Redis health check failed: {e}")
            return ServiceStatus(
                name="redis",
                status="unhealthy",
                message=f"Redis connection failed: {e!s}",
                response_time_ms=round(response_time, 2),
            )

    async def check_storage(self) -> ServiceStatus:
        """Check Google Cloud Storage connectivity."""
        start = time.time()
        try:
            client = storage.Client()
            # Just list buckets to verify credentials and connectivity
            list(client.list_buckets(max_results=1))
            response_time = (time.time() - start) * 1000
            return ServiceStatus(
                name="storage",
                status="healthy",
                message="Google Cloud Storage connection successful",
                response_time_ms=round(response_time, 2),
            )
        except Exception as e:
            response_time = (time.time() - start) * 1000
            logger.error(f"Storage health check failed: {e}")
            return ServiceStatus(
                name="storage",
                status="unhealthy",
                message=f"Storage connection failed: {e!s}",
                response_time_ms=round(response_time, 2),
            )

    async def get_health_status(self) -> HealthCheckResponse:
        """
        Get comprehensive health status of all services.

        Returns:
            HealthCheckResponse with overall status and individual service statuses.
        """
        # Check all services
        db_status = await self.check_database()
        redis_status = await self.check_redis()
        storage_status = await self.check_storage()

        services = {
            "database": db_status,
            "redis": redis_status,
            "storage": storage_status,
        }

        # Determine overall status
        unhealthy_count = sum(1 for s in services.values() if s.status == "unhealthy")
        if unhealthy_count == 0:
            overall_status = "healthy"
        elif unhealthy_count == len(services):
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"

        return HealthCheckResponse(
            status=overall_status,
            version="1.0.0",
            environment=settings.ENVIRONMENT,
            services=services,
            timestamp=datetime.now(tz=UTC).isoformat(),
        )
