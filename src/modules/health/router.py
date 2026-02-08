from fastapi import APIRouter, status

from src.modules.health.schemas import HealthCheckResponse, LivenessResponse, ReadinessResponse
from src.modules.health.service import HealthCheckService

router = APIRouter(prefix="/api/v1/health", tags=["Health"])


@router.get(
    "/",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete Health Check",
    description="Check health status of all system components including database, redis, and storage.",
)
async def health_check():
    """
    Comprehensive health check endpoint.

    Returns detailed status for:
    - Database (PostgreSQL)
    - Cache (Redis)
    - Storage (Google Cloud Storage)

    Status values:
    - healthy: All services operational
    - degraded: Some services down
    - unhealthy: All services down
    """
    service = HealthCheckService()
    return await service.get_health_status()


@router.get(
    "/live",
    response_model=LivenessResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Simple liveness check for Kubernetes/container orchestration.",
)
async def liveness():
    """
    Kubernetes liveness probe endpoint.

    Returns 200 if application is alive and running.
    Does not check external dependencies.
    """
    return LivenessResponse(status="ok")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness Probe",
    description="Check if application is ready to serve requests.",
)
async def readiness():
    """
    Kubernetes readiness probe endpoint.

    Checks critical dependencies (database, redis).
    Returns 200 if ready, 503 if not ready.
    """
    service = HealthCheckService()
    db_status = await service.check_database()
    redis_status = await service.check_redis()

    ready = db_status.status == "healthy" and redis_status.status == "healthy"

    if not ready:
        return ReadinessResponse(
            status="not_ready",
            ready=False,
        )

    return ReadinessResponse(
        status="ready",
        ready=True,
    )
