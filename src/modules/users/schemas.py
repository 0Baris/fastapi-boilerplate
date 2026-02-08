from pydantic import EmailStr, field_validator

from src.core.schema import BaseSchema
from src.core.utils.timezone import validate_timezone


class UserResponse(BaseSchema):
    id: str
    email: EmailStr
    full_name: str | None = None
    profile_image: str | None = None
    is_active: bool
    is_verified: bool
    provider: str
    timezone: str


class UserUpdate(BaseSchema):
    full_name: str | None = None
    profile_image: str | None = None
    timezone: str | None = None

    @field_validator("timezone")
    @classmethod
    def validate_timezone_value(cls, v: str | None) -> str | None:
        """Validate that the timezone is a valid IANA timezone string."""
        if v is None:
            return v
        if not validate_timezone(v):
            raise ValueError(f"Invalid timezone: {v}. Please provide a valid IANA timezone (e.g., 'Europe/Istanbul')")
        return v
