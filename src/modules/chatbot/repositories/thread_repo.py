import uuid
from datetime import datetime

from dateutil.tz import UTC
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.repository import BaseRepository
from src.modules.chatbot.models import ChatThread


class ThreadRepository(BaseRepository[ChatThread]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ChatThread)

    async def create_for_user(self, user_id: uuid.UUID, title: str | None = None) -> ChatThread:
        thread = ChatThread(user_id=user_id, title=title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        return await self.create(thread)

    async def get_by_user(
        self, user_id: uuid.UUID, include_archived: bool = False, skip: int = 0, limit: int = 50
    ) -> list[ChatThread]:
        query = select(self.model).where(self.model.user_id == user_id)

        if not include_archived:
            query = query.where(self.model.is_archived.is_(False))

        query = query.order_by(self.model.updated_at.desc()).offset(skip).limit(limit)

        result = await self.db.scalars(query)
        return list(result.all())

    async def get_user_thread(self, thread_id: uuid.UUID, user_id: uuid.UUID) -> ChatThread | None:
        result = await self.db.scalars(
            select(self.model).where(self.model.id == thread_id).where(self.model.user_id == user_id)
        )
        return result.one_or_none()

    async def search_threads(self, user_id: uuid.UUID, search_term: str, limit: int = 20) -> list[ChatThread]:
        """Search threads by title.

        Args:
            user_id: UUID of the user
            search_term: Search term (wildcards % and _ will be escaped)
            limit: Maximum number of results

        Returns:
            List of ChatThread objects matching the search
        """
        # Escape backslash first, then wildcards
        safe_search = search_term.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")

        result = await self.db.scalars(
            select(self.model)
            .where(self.model.user_id == user_id)
            .where(self.model.title.ilike(f"%{safe_search}%"))
            .order_by(self.model.updated_at.desc())
            .limit(limit)
        )
        return list(result.all())

    async def count_user_threads(self, user_id: uuid.UUID, include_archived: bool = False) -> int:
        from sqlalchemy import func

        query = select(func.count(self.model.id)).where(self.model.user_id == user_id)

        if not include_archived:
            query = query.where(self.model.is_archived.is_(False))

        result = await self.db.scalar(query)
        return result or 0

    async def archive_thread(self, thread_id: uuid.UUID) -> None:
        await self.db.execute(
            update(self.model)
            .where(self.model.id == thread_id)
            .values(is_archived=True, updated_at=datetime.now(tz=UTC))
        )

    async def update_title_no_commit(self, thread_id: uuid.UUID, title: str) -> None:
        await self.db.execute(
            update(self.model).where(self.model.id == thread_id).values(title=title, updated_at=datetime.now(tz=UTC))
        )

    async def increment_message_count_no_commit(self, thread_id: uuid.UUID, count: int = 1) -> None:
        await self.db.execute(
            update(self.model)
            .where(self.model.id == thread_id)
            .values(message_count=self.model.message_count + count, updated_at=datetime.now(tz=UTC))
        )

    async def touch_no_commit(self, thread_id: uuid.UUID) -> None:
        await self.db.execute(
            update(self.model).where(self.model.id == thread_id).values(updated_at=datetime.now(tz=UTC))
        )
