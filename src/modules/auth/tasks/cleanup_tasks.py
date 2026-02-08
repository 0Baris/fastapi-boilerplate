"""Celery tasks for cleaning up expired refresh tokens."""

from src.core.celery import celery_app
from src.core.database import AsyncSessionLocal
from src.core.logging import get_logger
from src.modules.auth.repositories.refresh_token_repo import RefreshTokenRepository

logger = get_logger(__name__)


@celery_app.task(name="auth.cleanup_expired_refresh_tokens")
async def cleanup_expired_refresh_tokens() -> dict[str, int]:
    """Delete expired refresh tokens from database.

    This task runs every 6 hours to clean up expired tokens and prevent
    database bloat. Tokens are automatically expired after 30 days.

    Returns:
        Dictionary with count of deleted tokens
    """
    async with AsyncSessionLocal() as session:
        repo = RefreshTokenRepository(session)
        deleted_count = await repo.cleanup_expired_tokens()

        logger.info(f"Cleaned up {deleted_count} expired refresh tokens")

        return {"deleted_count": deleted_count}
