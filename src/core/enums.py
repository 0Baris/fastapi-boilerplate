"""Core enums used across the application."""

from enum import Enum as PyEnum


class AuthProviderEnum(str, PyEnum):
    """Authentication provider types."""

    EMAIL = "email"
    GOOGLE = "google"
    APPLE = "apple"
