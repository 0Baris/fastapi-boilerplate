from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


def _load_secret(name: str) -> str:
    """Read a Cloud Run volume-mounted secret, falling back to env var.

    Cloud Run mounts each Secret Manager secret as a file under /secrets/<NAME>.
    Some module layouts mount the path as a directory whose inner file is
    /secrets/<NAME>/<NAME>, so probe that when the outer path is a directory.
    Outside Cloud Run (local dev, CI) the same value comes from the process
    environment, so the loader is transparent. Empty string means "unset".
    """
    path = Path(f"/secrets/{name}")
    if path.is_file():
        value = path.read_text().strip()
        if not value:
            logger.warning("Volume secret %s exists at %s but is empty", name, path)
        return value
    if path.is_dir():
        inner = path / name
        if inner.is_file():
            value = inner.read_text().strip()
            if not value:
                logger.warning("Volume secret %s exists at %s but is empty", name, inner)
            return value
    return os.environ.get(name, "")


def _load_secrets_from_gcp() -> dict[str, str]:
    """Load secrets from Google Cloud Secret Manager.

    Expects a single secret in .env format (KEY=VALUE per line). Only called
    when USE_SECRET_MANAGER=true and both GCP_PROJECT_ID and GCP_SECRET_NAME
    are set. Returns a dict of env_var_name -> secret_value.
    """
    secrets: dict[str, str] = {}

    project_id = os.getenv("GCP_PROJECT_ID")
    secret_name = os.getenv("GCP_SECRET_NAME")

    if not project_id or not secret_name:
        logger.warning("GCP_PROJECT_ID / GCP_SECRET_NAME not set, skipping Secret Manager")
        return secrets

    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        secret_data = response.payload.data.decode("UTF-8")

        for raw_line in secret_data.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            secrets[key] = value

        logger.info("Loaded %d secrets from Secret Manager (%s)", len(secrets), secret_name)

    except ImportError:
        logger.error("google-cloud-secret-manager not installed")
    except Exception as e:
        logger.error("Failed to load secrets from GCP: %s", e)

    return secrets


# Populate the environment from Secret Manager + volume mounts BEFORE Settings()
# reads it, so pydantic-settings picks values up uniformly. Outside Cloud Run /
# Secret Manager these are no-ops and the existing os.environ value (if any) wins.
if os.getenv("USE_SECRET_MANAGER", "").lower() == "true":
    for _key, _val in _load_secrets_from_gcp().items():
        if _key not in os.environ:
            os.environ[_key] = _val

_VOLUME_MOUNT_SECRETS = ("SECRET_KEY", "JWT_OLD_KEY", "DB_PASSWORD", "ZEPTOMAIL_API_KEY")
for _name in _VOLUME_MOUNT_SECRETS:
    _value = _load_secret(_name)
    if _value and _name not in os.environ:
        os.environ[_name] = _value


class Settings(BaseSettings):
    USE_SECRET_MANAGER: bool = Field(default=False, description="Load secrets from Google Cloud Secret Manager")
    GCP_PROJECT_ID: str | None = Field(default=None, description="GCP project id for Secret Manager")
    GCP_SECRET_NAME: str | None = Field(default=None, description="Secret Manager secret name (.env-format payload)")

    SWAGGER_USER: str = Field(description="Swagger UI username", default="admin")
    SWAGGER_PASSWORD: str = Field(description="Swagger UI password", default="password")

    ENVIRONMENT: str = Field(description="Environment type", default="development")
    PROJECT_NAME: str = Field(description="Project name", default="FastAPI App")
    API_V1_STR: str = Field(description="API version string", default="/api/v1")

    SECRET_KEY: str = Field(description="Secret key for JWT", default="your-secret-key")
    ALGORITHM: str = Field(description="Algorithm for JWT", default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, description="Refresh token expiration in days")

    # JWT versioned signing — graceful key rotation via the `kid` header.
    JWT_KEY_ID: str = Field(default="v1", description="Current JWT signing key id (kid claim)")
    JWT_OLD_KEY: str = Field(default="", description="Previous signing key, honored during grace window")
    JWT_OLD_KEY_ID: str = Field(default="", description="Previous JWT key id")
    JWT_OLD_KEY_VALID_UNTIL: str = Field(default="", description="ISO-8601 instant after which the old key is rejected")

    DATABASE_URL: str = Field(
        description="Database connection URL (DSN mode)",
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/fastapi_boilerplate",
    )
    # Cloud SQL Python Connector wiring. When INSTANCE_CONNECTION_NAME is set the
    # engine uses the Connector (in-band mTLS) instead of DATABASE_URL.
    INSTANCE_CONNECTION_NAME: str = Field(default="", description="Cloud SQL instance, e.g. project:region:instance")
    DB_USER: str = Field(default="", description="Cloud SQL DB user (Connector mode)")
    DB_PASSWORD: str = Field(default="", description="Cloud SQL DB password (Connector mode)")
    DB_NAME: str = Field(default="", description="Cloud SQL DB name (Connector mode)")
    DB_POOL_SIZE: int = Field(default=20, description="SQLAlchemy async pool size (DSN mode)")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Pool acquire timeout in seconds")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Pool overflow above DB_POOL_SIZE")

    REDIS_URL: str = Field(description="Redis connection URL", default="redis://localhost:6379")
    BACKEND_CORS_ORIGINS: list[AnyHttpUrl] = Field(description="Allowed CORS origins", default=[])

    TRUSTED_PROXIES: str = Field(
        default="10.0.0.0/8,172.16.0.0/12,192.168.0.0/16",
        description="Comma-separated CIDRs whose X-Forwarded-For is trusted",
    )
    TRUSTED_PROXY_HOP_COUNT: int = Field(
        default=0,
        description=(
            "Trusted proxy hops the edge LB appends to X-Forwarded-For. When >0, the client IP is read "
            "at a fixed offset from the right (spoof-proof). Set 1 behind Google External HTTPS LB. 0 = CIDR-walk."
        ),
    )

    GOOGLE_API_KEY: str = Field(description="Google API key", default="your-google-api-key")
    GEMINI_MODEL: str = "gemini-3-pro-preview"

    GEMINI_MODEL_HIGH: str = Field(description="Gemini model for high priority tasks", default="gemini-3-pro-preview")
    GEMINI_MODEL_LOW: str = Field(
        description="Gemini model for low priority tasks (default)", default="gemini-2.5-flash-lite"
    )

    GEMINI_CHAT_MODEL: str = Field(description="Gemini model for chatbot", default="gemini-3-flash-preview")
    CHAT_RATE_LIMIT_PER_MINUTE: int = Field(default=10, description="Max chat messages per minute per user")
    CHAT_DAILY_MESSAGE_LIMIT: int = Field(default=100, description="Max chat messages per day per user")
    CHAT_MAX_FILE_SIZE_MB: int = Field(default=20, description="Max file upload size in MB")
    CHAT_SLIDING_WINDOW_SIZE: int = Field(default=10, description="Number of recent messages to keep in full context")
    CHAT_SUMMARY_TRIGGER_COUNT: int = Field(
        default=50, description="Create summary after this many messages in a thread"
    )
    CHAT_HEALTH_CONTEXT_DAYS: int = Field(default=7, description="Days of health data to include in chat context")
    CHAT_MODERATION_ENABLED: bool = Field(default=True, description="Enable AI content moderation")

    GOOGLE_CLIENT_ID: str = Field(
        description="Google client ID",
        default="your-google-client-id.apps.googleusercontent.com",
    )
    APPLE_BUNDLE_ID: str = Field(description="Apple bundle ID", default="com.example.app")
    APPLE_SERVICE_ID: str = Field(description="Apple service ID", default="com.example.service")

    GOOGLE_APPLICATION_CREDENTIALS_BASE64: str | None = None

    # Email service settings (optional - use AWS SES or other providers)
    ZEPTOMAIL_BASE_URL: str | None = None
    ZEPTOMAIL_API_KEY: str | None = None
    ZEPTOMAIL_FROM_EMAIL: str = Field(default="noreply@example.com")
    ZEPTOMAIL_FROM_NAME: str = Field(default="FastAPI App")

    ZOHO_RESET_PASSWORD_TEMPLATE: str | None = None
    ZOHO_WELCOME_EMAIL_TEMPLATE: str | None = None
    ZOHO_VERIFICATION_CODE_TEMPLATE: str | None = None

    # Google Cloud Storage Configuration
    PUBLIC_BUCKET_NAME: str = Field(default="public-bucket", description="GCS public bucket name")
    PRIVATE_BUCKET_NAME: str = Field(default="private-bucket", description="GCS private bucket name")

    ENABLE_DOCS: bool = Field(default=True)
    USE_AI_REVISION: bool = Field(default=True, description="Enable AI-powered daily workout revision analysis")

    # Debug/Development flags - NEVER enable in production!
    DEBUG_RETURN_VERIFICATION_CODE: bool = Field(
        default=False,
        description="Return verification code in response (for testing when email service is down). NEVER enable in production!",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def _enforce_production_guards(self) -> None:
        """Boot-time guard rails. Crash on startup rather than ship a backdoor."""
        if self.ENVIRONMENT == "production":
            if self.DEBUG_RETURN_VERIFICATION_CODE:
                raise RuntimeError(
                    "DEBUG_RETURN_VERIFICATION_CODE=true is forbidden in production; it leaks verification codes."
                )
            if self.SECRET_KEY in {"your-secret-key", "MY_SUPER_SECRET_KEY"}:
                raise RuntimeError("SECRET_KEY must be overridden in production")
            if self.SWAGGER_PASSWORD in {"password", ""}:
                raise RuntimeError("SWAGGER_PASSWORD must be overridden in production")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()  # ty:ignore[missing-argument]
settings._enforce_production_guards()


def get_config_value(key: str, default: Any = None) -> Any:
    import warnings

    warnings.warn(
        "Config.get() is deprecated. Use settings.FIELD_NAME directly instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return getattr(settings, key, default)
