import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.repository import BaseRepository
from src.modules.chatbot.models import ModerationLog


class ModerationLogRepository(BaseRepository[ModerationLog]):
    """Repository for moderation log operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, ModerationLog)

    async def log_moderation_check(
        self,
        user_id: uuid.UUID,
        message_content: str,
        is_blocked: bool,
        category: str | None = None,
        reason: str | None = None,
        detection_method: str = "ai",
    ) -> ModerationLog:
        """Log a moderation check for analytics."""
        log = ModerationLog(
            user_id=user_id,
            message_content=message_content,
            is_blocked=is_blocked,
            category=category,
            reason=reason,
            detection_method=detection_method,
        )
        return await self.create(log)

    async def get_user_blocked_count(self, user_id: uuid.UUID, days: int = 7) -> int:
        """Get count of blocked messages for a user in last N days."""
        since = datetime.now(UTC) - timedelta(days=days)
        result = await self.db.scalar(
            select(func.count(self.model.id))
            .where(self.model.user_id == user_id)
            .where(self.model.is_blocked.is_(True))
            .where(self.model.created_at >= since)
        )
        return result or 0

    async def get_blocked_by_category(self, days: int = 30) -> dict[str, int]:
        """Get blocked message counts by category for analytics."""
        since = datetime.now(UTC) - timedelta(days=days)
        result = await self.db.execute(
            select(self.model.category, func.count(self.model.id))
            .where(self.model.is_blocked.is_(True))
            .where(self.model.category.isnot(None))
            .where(self.model.created_at >= since)
            .group_by(self.model.category)
        )

        return {row[0]: row[1] for row in result.all()}
