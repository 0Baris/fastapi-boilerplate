from pydantic import BaseModel, Field


class ServiceStatus(BaseModel):
    """Individual service health status."""

    name: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status: healthy, unhealthy, degraded")
    message: str | None = Field(None, description="Additional status information")
    response_time_ms: float | None = Field(None, description="Response time in milliseconds")


class HealthCheckResponse(BaseModel):
    """Complete health check response."""

    status: str = Field(..., description="Overall status: healthy, unhealthy, degraded")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment: development, staging, production")
    services: dict[str, ServiceStatus] = Field(..., description="Individual service statuses")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


class LivenessResponse(BaseModel):
    """Simple liveness probe response."""

    status: str = Field(default="ok", description="Application is alive")


class ReadinessResponse(BaseModel):
    """Simple readiness probe response."""

    status: str = Field(..., description="Application readiness: ready, not_ready")
    ready: bool = Field(..., description="Whether application is ready to serve requests")
