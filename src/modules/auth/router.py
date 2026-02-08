from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.middlewares.ratelimit import (
    RateLimiter,
    rate_limit_auth,
    rate_limit_email_verification,
    rate_limit_password_reset,
    rate_limit_registration,
)
from src.core.schema import ErrorResponse
from src.core.services.redis_service import RedisService, get_redis_service
from src.modules.auth.dependencies import get_current_user
from src.modules.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutAllRequest,
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    ResendCodeRequest,
    ResetPasswordRequest,
    ResetTokenResponse,
    SocialLoginRequest,
    TokenResponse,
    VerifyEmailRequest,
    VerifyResetCodeRequest,
)
from src.modules.auth.service import AuthService
from src.modules.users.models import User

router = APIRouter()


def get_client_info(request: Request) -> dict[str, str | None]:
    """Extract device and client information from request headers.

    Args:
        request: FastAPI Request object

    Returns:
        Dictionary with device_id, device_name, user_agent, ip_address
    """
    return {
        "device_id": request.headers.get("X-Device-ID"),
        "device_name": request.headers.get("X-Device-Name"),
        "user_agent": request.headers.get("User-Agent"),
        "ip_address": request.client.host if request.client else None,
    }


@router.post(
    path="/register",
    dependencies=[Depends(rate_limit_registration)],
    summary="Register a new user",
    description="Register a new user using email and password",
    response_model=MessageResponse,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Email already registered.",
        },
    },
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_service),
):
    auth_service = AuthService(db, redis)
    return await auth_service.register_email(register_data=request)


@router.post(
    path="/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit_auth)],
    summary="Login a user",
    description="Login a user using email and password",
    responses={
        403: {
            "model": ErrorResponse,
            "description": "Your account is not verified.",
        },
    },
)
async def login(
    request_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_service),
):
    auth_service = AuthService(db, redis)
    client_info = get_client_info(request)
    return await auth_service.authenticate_email(login_data=request_data, **client_info)


@router.post(
    path="/google",
    dependencies=[Depends(rate_limit_auth)],
    summary="Authenticate user using Google OAuth2 token",
    description="Authenticate user using Google OAuth2 token",
    response_model=TokenResponse,
)
async def google_auth(
    request_data: SocialLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_service),
):
    auth_service = AuthService(db, redis)
    client_info = get_client_info(request)
    return await auth_service.authenticate_google(request_data.access_token, **client_info)


@router.post(
    path="/apple",
    dependencies=[Depends(rate_limit_auth)],
    summary="Authenticate user using Apple Sign-In token",
    description="Authenticate user using Apple Sign-In token",
    response_model=TokenResponse,
)
async def apple_auth(
    request_data: SocialLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_service),
):
    auth_service = AuthService(db, redis)
    client_info = get_client_info(request)
    return await auth_service.authenticate_apple(request_data.access_token, **client_info)


@router.post(
    "/verify-email",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit_email_verification)],
    summary="Verify user's email",
    description="Verify user's email using the verification code",
)
async def verify_email(
    request_data: VerifyEmailRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_service),
):
    auth_service = AuthService(db, redis)
    client_info = get_client_info(request)
    return await auth_service.verify_email(verify_data=request_data, **client_info)


@router.post(
    "/resend-code",
    summary="Resend code to user's email",
    dependencies=[Depends(rate_limit_email_verification)],
    response_model=MessageResponse,
    responses={
        429: {"model": ErrorResponse, "description": "Too many requests."},
    },
)
async def resend_code(
    request: ResendCodeRequest,
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_service),
):
    auth_service = AuthService(db, redis)
    return await auth_service.resend_verification_code(str(request.email))


@router.post(
    "/reset-password",
    summary="Set new password",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit_password_reset)],
)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_service),
):
    auth_service = AuthService(db, redis)
    return await auth_service.reset_password(request)


@router.post(
    "/verify-reset-code",
    dependencies=[Depends(rate_limit_password_reset)],
    summary="Verify reset password code",
    response_model=ResetTokenResponse,
)
async def verify_reset_code(
    request: VerifyResetCodeRequest,
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_service),
):
    auth_service = AuthService(db, redis)
    return await auth_service.verify_reset_code(request)


@router.post(
    "/forgot-password",
    dependencies=[Depends(rate_limit_password_reset)],
    summary="Forgot password",
    description="Forgot password using the verification code",
    response_model=MessageResponse,
)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_service),
):
    auth_service = AuthService(db, redis)
    return await auth_service.forgot_password(str(request.email))


@router.post(
    "/refresh",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],
    summary="Refresh access token",
    description="Exchange refresh token for new access and refresh tokens",
    response_model=RefreshTokenResponse,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Invalid or expired refresh token",
        },
    },
)
async def refresh_token(
    request_data: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_service),
):
    auth_service = AuthService(db, redis)
    client_info = get_client_info(request)
    return await auth_service.refresh_access_token(
        refresh_token=request_data.refresh_token,
        **client_info,
    )


@router.post(
    "/logout",
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
    summary="Logout from current device",
    description="Revoke refresh token for current device",
    response_model=MessageResponse,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized",
        },
    },
)
async def logout(
    request_data: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_service),
):
    auth_service = AuthService(db, redis)
    return await auth_service.logout_device(
        user_id=current_user.id,
        refresh_token=request_data.refresh_token,
    )


@router.post(
    "/logout-all",
    dependencies=[Depends(RateLimiter(times=3, seconds=60))],
    summary="Logout from all devices",
    description="Revoke all refresh tokens for the user. Optionally keep current device logged in.",
    response_model=MessageResponse,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized",
        },
    },
)
async def logout_all(
    request_data: LogoutAllRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_service),
):
    auth_service = AuthService(db, redis)
    except_token = request_data.refresh_token if request_data.except_current else None
    return await auth_service.logout_all_devices(
        user_id=current_user.id,
        except_token=except_token,
    )
