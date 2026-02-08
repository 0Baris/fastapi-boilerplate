import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.core.repository import BaseRepository
from src.modules.chatbot.models import ChatMessage


class MessageRepository(BaseRepository[ChatMessage]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ChatMessage)

    async def create_message(
        self,
        thread_id: uuid.UUID,
        role: str,
        content: str,
        attachments: list[dict] | None = None,
        tokens_used: int | None = None,
        model_used: str | None = None,
        response_time_ms: int | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            thread_id=thread_id,
            role=role,
            content=content,
            attachments=attachments or [],
            tokens_used=tokens_used,
            model_used=model_used,
            response_time_ms=response_time_ms,
        )
        return await self.create(message)

    async def get_thread_messages(
        self, thread_id: uuid.UUID, limit: int = 50, before_timestamp: datetime | None = None
    ) -> list[ChatMessage]:
        """Get thread messages with media attachments eagerly loaded."""
        query = select(self.model).options(joinedload(ChatMessage.media)).where(self.model.thread_id == thread_id)

        if before_timestamp:
            query = query.where(self.model.created_at < before_timestamp)

        query = query.order_by(self.model.created_at.desc()).limit(limit)

        result = await self.db.scalars(query)
        messages = list(result.unique().all())

        return list(reversed(messages))

    async def get_recent_messages(self, thread_id: uuid.UUID, limit: int = 10) -> list[ChatMessage]:
        """Get recent messages with media attachments eagerly loaded."""
        result = await self.db.scalars(
            select(self.model)
            .options(joinedload(ChatMessage.media))
            .where(self.model.thread_id == thread_id)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        messages = list(result.unique().all())
        return list(reversed(messages))

    async def count_thread_messages(self, thread_id: uuid.UUID) -> int:
        from sqlalchemy import func

        result = await self.db.scalar(select(func.count(self.model.id)).where(self.model.thread_id == thread_id))
        return result or 0

    async def search_in_thread(self, thread_id: uuid.UUID, search_term: str, limit: int = 50) -> list[ChatMessage]:
        """Search messages in a thread by content.

        Args:
            thread_id: UUID of the thread
            search_term: Search term (wildcards % and _ will be escaped)
            limit: Maximum number of results

        Returns:
            List of ChatMessage objects matching the search
        """
        # Escape backslash first, then wildcards
        safe_search = search_term.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")

        result = await self.db.scalars(
            select(self.model)
            .where(self.model.thread_id == thread_id)
            .where(self.model.content.ilike(f"%{safe_search}%"))
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        return list(result.all())

    async def get_last_message(self, thread_id: uuid.UUID) -> ChatMessage | None:
        result = await self.db.scalars(
            select(self.model).where(self.model.thread_id == thread_id).order_by(self.model.created_at.desc()).limit(1)
        )
        return result.one_or_none()
