import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.modules.chatbot.enums import MessageRole

if TYPE_CHECKING:
    from src.modules.chatbot.models.chat_thread import ChatThread
    from src.modules.chatbot.models.media_upload import MediaUpload


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False, index=True
    )

    role: Mapped[MessageRole] = mapped_column(String(length=20), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    attachments: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)

    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(length=100), nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    thread: Mapped["ChatThread"] = relationship("ChatThread", back_populates="messages")
    media: Mapped[list["MediaUpload"]] = relationship(
        "MediaUpload", back_populates="message", cascade="all, delete-orphan"
    )
