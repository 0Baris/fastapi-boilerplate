import re
import uuid

from pydantic import EmailStr, Field, field_validator

from src.core.schema import BaseSchema


class SocialLoginRequest(BaseSchema):
    access_token: str


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str


class RegisterRequest(BaseSchema):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        description="Password must be at least 8 characters long",
    )

    @field_validator("password")
    def validate_password_strength(cls, v):
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("Password must contain both letters and numbers")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class ForgotPasswordRequest(BaseSchema):
    email: EmailStr


class ResendCodeRequest(BaseSchema):
    email: EmailStr


class VerifyEmailRequest(BaseSchema):
    email: EmailStr
    code: str = Field(
        ...,
        min_length=4,
        max_length=4,
        pattern=r"^\d{4}$",
        description="4-digit verification code",
    )


class VerifyResetCodeRequest(BaseSchema):
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")


class ResetPasswordRequest(BaseSchema):
    reset_token: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    def validate_new_password_strength(cls, v):
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("Password must contain both letters and numbers")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class RefreshTokenRequest(BaseSchema):
    refresh_token: str = Field(..., description="Refresh token to exchange for new access token")


class LogoutRequest(BaseSchema):
    refresh_token: str = Field(..., description="Refresh token to revoke")


class LogoutAllRequest(BaseSchema):
    except_current: bool = Field(
        default=False, description="If true, keep current device logged in (requires refresh_token)"
    )
    refresh_token: str | None = Field(default=None, description="Current device's refresh token to keep active")


# Responses


class MessageResponse(BaseSchema):
    message: str = "Success"
    debug_code: str | None = None  # Only populated when DEBUG_RETURN_VERIFICATION_CODE=true


class RegisterResponse(BaseSchema):
    id: uuid.UUID
    email: str
    full_name: str | None = None
    message: str = "Registration successful. Please verify your email."
    debug_code: str | None = None  # Only populated when DEBUG_RETURN_VERIFICATION_CODE=true


class LoginResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    is_new_user: bool


class ForgotPasswordResponse(BaseSchema):
    message: str = "Verification code sent to your email"
    debug_code: str | None = None  # Only populated when DEBUG_RETURN_VERIFICATION_CODE=true


class ResendCodeResponse(BaseSchema):
    message: str = "Verification code resent to your email"
    debug_code: str | None = None  # Only populated when DEBUG_RETURN_VERIFICATION_CODE=true


class ResetPasswordResponse(BaseSchema):
    message: str = "Password reset successful"


class UserProfileResponse(BaseSchema):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None
    profile_image: str
    is_active: bool


class VerifyResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    is_new_user: bool


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str
    is_new_user: bool


class RefreshTokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ResetTokenResponse(BaseSchema):
    reset_token: str
    token_type: str = "bearer"
