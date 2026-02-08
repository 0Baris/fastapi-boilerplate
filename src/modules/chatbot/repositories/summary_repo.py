import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.repository import BaseRepository
from src.modules.chatbot.models import ChatSummary


class SummaryRepository(BaseRepository[ChatSummary]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ChatSummary)

    async def create_summary(
        self,
        thread_id: uuid.UUID,
        message_start_id: uuid.UUID,
        message_end_id: uuid.UUID,
        message_count: int,
        summary: str,
        model_used: str = "gemini-2.0-flash-exp",
        tokens_used: int | None = None,
    ) -> ChatSummary:
        summary_obj = ChatSummary(
            thread_id=thread_id,
            message_start_id=message_start_id,
            message_end_id=message_end_id,
            message_count=message_count,
            summary=summary,
            model_used=model_used,
            tokens_used=tokens_used,
        )
        return await self.create(summary_obj)

    async def get_latest(self, thread_id: uuid.UUID) -> ChatSummary | None:
        result = await self.db.scalars(
            select(self.model).where(self.model.thread_id == thread_id).order_by(self.model.created_at.desc()).limit(1)
        )
        return result.one_or_none()

    async def get_all_summaries(self, thread_id: uuid.UUID) -> list[ChatSummary]:
        result = await self.db.scalars(
            select(self.model).where(self.model.thread_id == thread_id).order_by(self.model.created_at)
        )
        return list(result.all())

    async def has_summary(self, thread_id: uuid.UUID) -> bool:
        from sqlalchemy import func

        count = await self.db.scalar(select(func.count(self.model.id)).where(self.model.thread_id == thread_id))
        return (count or 0) > 0

    async def count_summaries(self, thread_id: uuid.UUID) -> int:
        from sqlalchemy import func

        result = await self.db.scalar(select(func.count(self.model.id)).where(self.model.thread_id == thread_id))
        return result or 0
