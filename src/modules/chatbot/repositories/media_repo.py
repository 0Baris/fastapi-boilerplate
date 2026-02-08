import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.repository import BaseRepository
from src.modules.chatbot.models import MediaUpload


class MediaRepository(BaseRepository[MediaUpload]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, MediaUpload)

    async def create_pending_upload(
        self,
        user_id: uuid.UUID,
        original_filename: str,
        storage_path: str,
        mime_type: str,
        file_size_bytes: int,
    ) -> MediaUpload:
        """Create upload record without message_id (pending state)."""
        media = MediaUpload(
            user_id=user_id,
            message_id=None,
            original_filename=original_filename,
            storage_path=storage_path,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            processing_status="pending",
        )
        return await self.create(media)

    async def attach_to_message_no_commit(self, upload_id: uuid.UUID, message_id: uuid.UUID) -> MediaUpload | None:
        """Link pending upload to a message."""
        await self.db.execute(
            update(self.model)
            .where(self.model.id == upload_id)
            .values(message_id=message_id, processing_status="attached")
        )

        result = await self.db.scalars(select(self.model).where(self.model.id == upload_id))
        return result.one_or_none()

    async def get_by_message(self, message_id: uuid.UUID) -> list[MediaUpload]:
        """Get all media attached to a message."""
        result = await self.db.scalars(
            select(self.model).where(self.model.message_id == message_id).order_by(self.model.created_at)
        )
        return list(result.all())

    async def get_pending_uploads(self, user_id: uuid.UUID, created_after: datetime) -> list[MediaUpload]:
        """Get user's recent pending uploads (for cleanup)."""
        result = await self.db.scalars(
            select(self.model)
            .where(self.model.user_id == user_id)
            .where(self.model.message_id.is_(None))
            .where(self.model.processing_status == "pending")
            .where(self.model.created_at >= created_after)
        )
        return list(result.all())

    async def create_upload(
        self,
        user_id: uuid.UUID,
        message_id: uuid.UUID,
        original_filename: str,
        storage_path: str,
        mime_type: str,
        file_size_bytes: int,
    ) -> MediaUpload:
        media = MediaUpload(
            user_id=user_id,
            message_id=message_id,
            original_filename=original_filename,
            storage_path=storage_path,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            processing_status="pending",
        )
        return await self.create(media)

    async def get_message_media(self, message_id: uuid.UUID) -> list[MediaUpload]:
        result = await self.db.scalars(
            select(self.model).where(self.model.message_id == message_id).order_by(self.model.created_at)
        )
        return list(result.all())

    async def get_user_media(
        self, user_id: uuid.UUID, mime_type: str | None = None, limit: int = 100
    ) -> list[MediaUpload]:
        """Get user's media uploads, optionally filtered by mime type prefix.

        Args:
            user_id: UUID of the user
            mime_type: Optional mime type prefix to filter by (e.g., "image/", "video/")
            limit: Maximum number of results

        Returns:
            List of MediaUpload objects
        """
        query = select(self.model).where(self.model.user_id == user_id)

        if mime_type:
            query = query.where(self.model.mime_type.startswith(mime_type))

        query = query.order_by(self.model.created_at.desc()).limit(limit)

        result = await self.db.scalars(query)
        return list(result.all())

    async def get_pending_processing(self, limit: int = 10) -> list[MediaUpload]:
        result = await self.db.scalars(
            select(self.model)
            .where(self.model.processing_status == "pending")
            .order_by(self.model.created_at)
            .limit(limit)
        )
        return list(result.all())

    async def update_status_no_commit(
        self,
        media_id: uuid.UUID,
        status: str,
        extracted_text: str | None = None,
        extracted_data: dict | None = None,
        error_message: str | None = None,
    ) -> None:
        values: dict[str, Any] = {"processing_status": status}

        if extracted_text:
            values["extracted_text"] = extracted_text
        if extracted_data:
            values["extracted_data"] = extracted_data
        if error_message:
            values["error_message"] = error_message

        await self.db.execute(update(self.model).where(self.model.id == media_id).values(**values))

    async def get_by_storage_path(self, storage_path: str) -> MediaUpload | None:
        result = await self.db.scalars(select(self.model).where(self.model.storage_path == storage_path))
        return result.one_or_none()
