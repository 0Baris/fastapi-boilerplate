"""Base User model - Core authentication and profile fields."""

import uuid

from sqlalchemy import Boolean, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.core.enums import AuthProviderEnum


class BaseUser(Base):
    """Base user model with authentication and basic profile fields.

    This is the core user model that other modules can extend.
    Contains only essential fields for authentication and user management.
    """

    __tablename__ = "users"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String, nullable=True)

    # Profile
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    profile_image: Mapped[str | None] = mapped_column(String, nullable=True)

    # Authentication
    provider: Mapped[AuthProviderEnum] = mapped_column(
        Enum(AuthProviderEnum, name="auth_provider_enum"),
        default=AuthProviderEnum.EMAIL,
        nullable=False,
    )
    social_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notification_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    timezone: Mapped[str] = mapped_column(String, default="UTC", nullable=False)
