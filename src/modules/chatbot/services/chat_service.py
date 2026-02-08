import uuid
from datetime import datetime
from logging import Logger

from fastapi import WebSocket
from pydantic_ai import AudioUrl, DocumentUrl, ImageUrl, VideoUrl
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exception import NotFoundError
from src.core.logging import get_logger
from src.core.services.storage import storage_service
from src.modules.chatbot.repositories import MediaRepository, MessageRepository, SummaryRepository, ThreadRepository
from src.modules.chatbot.services.agent_service import ChatAgentService, FileAttachment
from src.modules.chatbot.services.context_service import ChatContextService
from src.modules.chatbot.services.moderation_service import ModerationService
from src.modules.users.models import User

logger: Logger = get_logger(__name__)


class ChatService:
    """Main orchestrator for chatbot operations.

    This service coordinates:
    - Thread management (create, load, list)
    - Message handling (user + AI responses)
    - Context building via ChatContextService
    - AI streaming via ChatAgentService
    - Content moderation via ModerationService
    - WebSocket communication
    """

    def __init__(self, db: AsyncSession):
        self.db: AsyncSession = db
        self.thread_repo = ThreadRepository(db)
        self.message_repo = MessageRepository(db)
        self.summary_repo = SummaryRepository(db)
        self.media_repo = MediaRepository(db)
        self.context_service = ChatContextService(db)
        self.agent_service = ChatAgentService()
        self.moderation_service = ModerationService(db)

    async def handle_send_message(
        self,
        user: User,
        thread_id: uuid.UUID | None,
        content: str,
        websocket: WebSocket,
        upload_ids: list[str] | None = None,
    ) -> dict:
        """Handle user message + AI response with streaming.

        FLOW:
        0. AI moderation check (FIRST)
        1. Create thread if new (thread_id=null)
        2. Save user message to DB
        2.5. Link file attachments to message
        3. Build context (history + health data)
        4. Stream AI response to WebSocket (with files)
        5. Save AI response to DB
        6. Update thread metadata
        7. Generate title if first message
        8. Check if summary needed

        Args:
            user: Current user
            thread_id: Existing thread UUID or None for new thread
            content: User's message text
            websocket: WebSocket for streaming responses
            upload_ids: Optional list of upload UUIDs to attach to message

        Returns:
            dict with thread_id and message_id

        WebSocket Events Sent:
            - {"type": "moderation_blocked", ...} (if blocked)
            - {"type": "thread_created", "thread_id": "..."}
            - {"type": "assistant_chunk", "content": "..."} (multiple times)
            - {"type": "message_complete", ...}
        """
        logger.info(f"User {user.id} sending message (thread_id={thread_id})")

        if settings.CHAT_MODERATION_ENABLED:
            is_safe, reason, category = await self.moderation_service.check_message_safety(
                message=content, user_id=user.id
            )

            if not is_safe:
                logger.warning(f"Blocked message: user={user.id}, category={category}")

                await self.db.commit()

                await websocket.send_json(
                    {
                        "type": "moderation_blocked",
                        "category": category,
                        "message": reason,
                    }
                )

                return {"blocked": True, "reason": reason, "category": category}

        if not thread_id:
            thread = await self.thread_repo.create_for_user(user_id=user.id, title="New Chat")
            thread_id = thread.id

            await websocket.send_json({"type": "thread_created", "thread_id": str(thread_id)})
            logger.info(f"Created new thread: {thread_id}")
        else:
            thread = await self.thread_repo.get_user_thread(thread_id, user.id)
            if not thread:
                raise NotFoundError("Thread not found or access denied")

        user_message = await self.message_repo.create_message(thread_id=thread_id, role="user", content=content)
        logger.debug(f"Saved user message: {user_message.id}")

        pydantic_ai_files: list[FileAttachment] = []
        failed_attachments: list[str] = []

        if upload_ids:
            for upload_id_str in upload_ids:
                try:
                    upload_id = uuid.UUID(upload_id_str)
                    upload = await self.media_repo.get(upload_id)

                    if not upload:
                        error_msg = f"Upload {upload_id_str[:8]}... not found"
                        logger.warning(f"Invalid upload_id: {upload_id}")
                        failed_attachments.append(error_msg)
                        continue

                    if upload.user_id != user.id:
                        error_msg = f"Upload {upload_id_str[:8]}... unauthorized"
                        logger.warning(f"Unauthorized upload_id: {upload_id}")
                        failed_attachments.append(error_msg)
                        continue

                    await self.media_repo.attach_to_message_no_commit(upload_id, user_message.id)
                    logger.debug(f"Attached upload {upload_id} to message {user_message.id}")

                    signed_url = await storage_service.generate_signed_url(upload.storage_path, expiration_minutes=120)
                    logger.debug(signed_url)

                    if upload.mime_type.startswith("image/"):
                        pydantic_ai_files.append(ImageUrl(url=signed_url))
                    elif upload.mime_type == "application/pdf" or upload.mime_type.startswith("text/"):
                        pydantic_ai_files.append(DocumentUrl(url=signed_url, media_type=upload.mime_type))
                    elif upload.mime_type.startswith("video/"):
                        pydantic_ai_files.append(VideoUrl(url=signed_url))
                    elif upload.mime_type.startswith("audio/"):
                        pydantic_ai_files.append(AudioUrl(url=signed_url))
                    else:
                        error_msg = f"File {upload.original_filename} has unsupported type"
                        logger.warning(f"Unsupported MIME type for AI: {upload.mime_type}")
                        failed_attachments.append(error_msg)

                except ValueError:
                    error_msg = f"Invalid upload ID format: {upload_id_str[:8]}..."
                    logger.warning(f"Invalid upload_id format: {upload_id_str}")
                    failed_attachments.append(error_msg)
                    continue

            logger.debug(f"Prepared {len(pydantic_ai_files)} files for AI, {len(failed_attachments)} failed")

            if failed_attachments:
                await websocket.send_json(
                    {
                        "type": "attachment_warning",
                        "message": f"{len(failed_attachments)} file(s) could not be attached",
                        "failed_files": failed_attachments,
                    }
                )

        system_instructions = await self.context_service.build_system_instructions(thread_id, user)
        logger.debug(f"Built system instructions ({len(system_instructions)} chars)")

        (full_response, tokens, time_ms) = await self.agent_service.stream_response(
            user_prompt=content,
            system_instructions=system_instructions,
            websocket=websocket,
            files=pydantic_ai_files if pydantic_ai_files else None,
        )

        ai_message = await self.message_repo.create_message(
            thread_id=thread_id,
            role="assistant",
            content=full_response,
            tokens_used=tokens,
            model_used=settings.GEMINI_CHAT_MODEL,
            response_time_ms=time_ms,
        )
        logger.debug(f"Saved AI message: {ai_message.id} ({tokens} tokens, {time_ms}ms)")

        # Check if we need to generate title BEFORE incrementing count
        should_generate_title = thread.message_count == 0

        await self.thread_repo.increment_message_count_no_commit(thread_id, count=2)
        await self.thread_repo.touch_no_commit(thread_id)

        if should_generate_title:
            title = await self.agent_service.generate_thread_title(content)
            await self.thread_repo.update_title_no_commit(thread_id, title)
            logger.debug(f"Generated thread title: {title}")

        await self.db.commit()

        await websocket.send_json(
            {
                "type": "message_complete",
                "message_id": str(ai_message.id),
                "thread_id": str(thread_id),
                "tokens_used": tokens,
                "response_time_ms": time_ms,
            }
        )

        msg_count = await self.message_repo.count_thread_messages(thread_id)
        if msg_count >= settings.CHAT_SUMMARY_TRIGGER_COUNT:
            logger.info(f"Thread {thread_id} has {msg_count} messages, generating summary...")
            try:
                # Get messages for summary
                messages = await self.message_repo.get_thread_messages(thread_id, limit=50)

                # Format messages for AI
                message_dicts = [{"role": msg.sender, "content": msg.content} for msg in messages]

                # Generate summary
                summary_text = await self.agent_service.generate_thread_summary(message_dicts)

                # Save summary to database
                if messages:
                    await self.summary_repo.create_summary(
                        thread_id=thread_id,
                        message_start_id=messages[-1].id,
                        message_end_id=messages[0].id,
                        message_count=len(messages),
                        summary=summary_text,
                        model_used=settings.GEMINI_MODEL_LOW,
                    )
                    logger.info(f"Summary created for thread {thread_id}")
            except Exception as e:
                logger.error(f"Failed to generate summary for thread {thread_id}: {e}", exc_info=True)

        return {"thread_id": str(thread_id), "message_id": str(ai_message.id)}

    async def handle_load_thread(self, user: User, thread_id: uuid.UUID, before_timestamp: datetime | None) -> dict:
        """Load thread messages with cursor pagination.

        Args:
            user: Current user (for ownership check)
            thread_id: Thread UUID to load
            before_timestamp: Load messages before this time (for pagination)

        Returns:
            dict with thread_id, messages array, and has_more flag
        """
        logger.info(f"Loading thread {thread_id} for user {user.id}")

        thread = await self.thread_repo.get_user_thread(thread_id, user.id)
        if not thread:
            raise NotFoundError("Thread not found or access denied")

        messages = await self.message_repo.get_thread_messages(
            thread_id=thread_id, limit=50, before_timestamp=before_timestamp
        )

        # Build messages with signed URLs for attachments
        message_list = []
        for msg in messages:
            attachments = []
            for media in msg.media:
                # Generate signed URL for secure access (1 hour expiry)
                signed_url = await storage_service.generate_signed_url(media.storage_path, expiration_minutes=60)
                attachments.append(
                    {
                        "id": str(media.id),
                        "filename": media.original_filename,
                        "url": signed_url,
                        "mime_type": media.mime_type,
                        "size_bytes": media.file_size_bytes,
                    }
                )

            message_list.append(
                {
                    "id": str(msg.id),
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                    "attachments": attachments,
                }
            )

        return {
            "thread_id": str(thread_id),
            "messages": message_list,
            "has_more": len(messages) == 50,
        }

    async def handle_list_threads(self, user: User, skip: int, limit: int) -> dict:
        """List user's chat threads.

        Args:
            user: Current user
            skip: Pagination offset
            limit: Max results

        Returns:
            dict with threads array and total count
        """
        logger.info(f"Listing threads for user {user.id} (skip={skip}, limit={limit})")

        threads = await self.thread_repo.get_by_user(user_id=user.id, include_archived=False, skip=skip, limit=limit)

        total = await self.thread_repo.count_user_threads(user.id)

        thread_list = []
        for thread in threads:
            last_msg = thread.messages[-1] if thread.messages else None
            thread_list.append(
                {
                    "id": str(thread.id),
                    "title": thread.title,
                    "last_message": last_msg.content[:100] if last_msg else "",
                    "updated_at": thread.updated_at.isoformat(),
                    "message_count": thread.message_count,
                }
            )

        return {"threads": thread_list, "total": total}
