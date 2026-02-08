from __future__ import annotations

import logging
from typing import Any

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    SWAGGER_USER: str = Field(description="Swagger UI username", default="admin")
    SWAGGER_PASSWORD: str = Field(description="Swagger UI password", default="password")

    ENVIRONMENT: str = Field(description="Environment type", default="development")
    PROJECT_NAME: str = Field(description="Project name", default="FastAPI App")
    API_V1_STR: str = Field(description="API version string", default="/api/v1")

    SECRET_KEY: str = Field(description="Secret key for JWT", default="your-secret-key")
    ALGORITHM: str = Field(description="Algorithm for JWT", default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, description="Refresh token expiration in days")

    DATABASE_URL: str = Field(
        description="Database connection URL",
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/fastapi_boilerplate",
    )
    REDIS_URL: str = Field(description="Redis connection URL", default="redis://localhost:6379")
    BACKEND_CORS_ORIGINS: list[AnyHttpUrl] = Field(description="Allowed CORS origins", default=[])

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

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()  # ty:ignore[missing-argument]


def get_config_value(key: str, default: Any = None) -> Any:
    import warnings

    warnings.warn(
        "Config.get() is deprecated. Use settings.FIELD_NAME directly instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return getattr(settings, key, default)
