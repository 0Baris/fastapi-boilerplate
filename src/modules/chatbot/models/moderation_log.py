import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ModerationLog(Base):
    """Log of all moderation checks for analytics and monitoring."""

    __tablename__ = "moderation_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    message_content: Mapped[str] = mapped_column(Text, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    detection_method: Mapped[str] = mapped_column(String(20), default="ai", nullable=False)
