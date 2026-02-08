import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ChatSummary(Base):
    __tablename__ = "chat_summaries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False, index=True
    )

    message_start_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    message_end_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False)

    summary: Mapped[str] = mapped_column(Text, nullable=False)

    model_used: Mapped[str] = mapped_column(String(length=100), nullable=False, default="gemini-3-flash-preview")
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = ()
