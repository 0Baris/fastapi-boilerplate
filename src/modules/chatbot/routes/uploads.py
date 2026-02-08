import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.core.logging import get_logger
from src.core.services.storage import storage_service
from src.modules.auth.dependencies import get_current_user
from src.modules.chatbot.repositories import MediaRepository
from src.modules.users.models import User

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chatbot"])

ALLOWED_MIME_TYPES = {
    # Images
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    # Documents
    "application/pdf",
    "text/plain",
    "text/csv",
    # Video
    "video/mp4",
    "video/webm",
    "video/quicktime",
    # Audio
    "audio/mpeg",
    "audio/wav",
    "audio/webm",
    "audio/ogg",
}


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload file for chat attachment.

    Upload images, documents, videos, or audio files to attach in chat messages.
    The AI can analyze image content, read documents, and transcribe audio.

    **Flow:**
    1. Upload file to this endpoint
    2. Receive upload_id in response
    3. Include upload_id in WebSocket send_message event
    4. AI processes file in conversation context
    """
    try:
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

        contents = await file.read()
        file_size = len(contents)

        max_size = settings.CHAT_MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_size:
            raise HTTPException(status_code=400, detail=f"File too large. Max size: {settings.CHAT_MAX_FILE_SIZE_MB}MB")

        if file_size == 0:
            raise HTTPException(status_code=400, detail="Empty file not allowed")

        file_obj = io.BytesIO(contents)
        storage_url = await storage_service.upload_file(
            file_obj=file_obj,
            filename=file.filename or "upload",
            content_type=file.content_type or "application/octet-stream",
            folder=f"chat_uploads/{current_user.id}",
            use_private=True,  # Use private bucket for chat uploads
        )

        logger.info(f"Uploaded file to GCS: {storage_url} (user={current_user.id}, size={file_size})")

        media_repo = MediaRepository(db)
        media_upload = await media_repo.create_pending_upload(
            user_id=current_user.id,
            original_filename=file.filename or "upload",
            storage_path=storage_url,
            mime_type=file.content_type or "application/octet-stream",
            file_size_bytes=file_size,
        )

        await db.commit()

        logger.info(f"Created pending upload: {media_upload.id} (user={current_user.id})")

        return {
            "upload_id": str(media_upload.id),
            "filename": media_upload.original_filename,
            "size_bytes": file_size,
            "storage_url": storage_url,
            "mime_type": media_upload.mime_type,
            "created_at": media_upload.created_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="File upload failed")
