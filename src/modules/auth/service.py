import uuid
from datetime import UTC, datetime, timedelta
from logging import Logger

import httpx
import jwt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from jwt import PyJWKClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.enums import AuthProviderEnum
from src.core.exception import AuthenticationError, AuthorizationError, BusinessRuleError, NotFoundError
from src.core.logging import get_logger
from src.core.security import security_service
from src.core.services.email_service import email_service
from src.core.services.redis_service import RedisService
from src.modules.auth.repositories.refresh_token_repo import RefreshTokenRepository
from src.modules.auth.schemas import ResetPasswordRequest, VerifyResetCodeRequest
from src.modules.users.models import User
from src.modules.users.repository import UserRepository
from src.utils.helpers import generate_verification_code

logger: Logger = get_logger(name=__name__)


class AuthService:
    def __init__(self, db: AsyncSession, redis: RedisService):
        self.db = db
        self.user_repo = UserRepository(db)
        self.refresh_token_repo = RefreshTokenRepository(db)
        self.redis: RedisService = redis

    async def _create_token_pair(
        self,
        user: User,
        device_id: str | None = None,
        device_name: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> dict:
        """Create access token and refresh token pair.

        Args:
            user: User object
            device_id: Unique device identifier from client
            device_name: Human-readable device name
            user_agent: User agent string from request
            ip_address: Client IP address

        Returns:
            Dictionary with access_token, refresh_token, token_type, and is_new_user
        """
        # Create access token (1 hour)
        access_token = security_service.create_access_token(subject=user.id)

        # Create refresh token (random string)
        refresh_token = security_service.create_refresh_token()
        token_hash = security_service.hash_token(refresh_token)

        # Calculate expiration
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        expires_at = datetime.now(UTC) + expires_delta

        # Save to database
        await self.refresh_token_repo.create_token(
            user_id=user.id,
            token_hash=token_hash,
            expires_delta=expires_delta,
            device_id=device_id,
            device_name=device_name,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        # Cache in Redis
        await self.redis.cache_refresh_token(
            token_hash=token_hash,
            user_id=str(user.id),
            expires_at=expires_at,
            device_id=device_id,
        )

        logger.info(f"Created token pair for user {user.id}, device: {device_id}")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def refresh_access_token(
        self,
        refresh_token: str,
        device_id: str | None = None,
        device_name: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> dict:
        """Refresh access token using refresh token with rotation.

        Implements token rotation and reuse detection. If a revoked token is reused,
        the entire token chain is invalidated for security.

        Args:
            refresh_token: Current refresh token
            device_id: Unique device identifier from client
            device_name: Human-readable device name
            user_agent: User agent string from request
            ip_address: Client IP address

        Returns:
            Dictionary with new access_token, refresh_token, token_type

        Raises:
            AuthenticationError: If token is invalid, expired, or revoked
        """
        # Hash the incoming token
        token_hash = security_service.hash_token(refresh_token)

        # Check cache first (fast path)
        cached_token = await self.redis.get_cached_token(token_hash)
        if cached_token:
            # Token exists in cache, check if it's valid
            is_valid = await self.refresh_token_repo.is_token_valid(token_hash)
            if not is_valid:
                # Token was revoked - check if it's being reused
                db_token = await self.refresh_token_repo.get_by_token_hash(token_hash)
                if db_token and db_token.is_revoked:
                    # CRITICAL: Reuse detection - revoke entire chain
                    await self.refresh_token_repo.revoke_token_chain(db_token.id)
                    await self.redis.invalidate_token_cache(token_hash)
                    logger.warning(
                        f"Refresh token reuse detected for user {db_token.user_id}, "
                        f"device: {device_id}. Revoking entire chain."
                    )
                    raise AuthenticationError("Token has been revoked. Please log in again.")

                raise AuthenticationError("Invalid or expired refresh token.")
        else:
            # Not in cache, validate from database
            is_valid = await self.refresh_token_repo.is_token_valid(token_hash)
            if not is_valid:
                db_token = await self.refresh_token_repo.get_by_token_hash(token_hash)
                if db_token and db_token.is_revoked:
                    # CRITICAL: Reuse detection - revoke entire chain
                    await self.refresh_token_repo.revoke_token_chain(db_token.id)
                    logger.warning(
                        f"Refresh token reuse detected for user {db_token.user_id}, "
                        f"device: {device_id}. Revoking entire chain."
                    )
                    raise AuthenticationError("Token has been revoked. Please log in again.")

                raise AuthenticationError("Invalid or expired refresh token.")

        # Get the token from database
        db_token = await self.refresh_token_repo.get_by_token_hash(token_hash)
        if not db_token:
            raise AuthenticationError("Invalid refresh token.")

        # Get user
        user = await self.user_repo.get(db_token.user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive.")

        # Create new token pair
        new_tokens = await self._create_token_pair(
            user=user,
            device_id=device_id or db_token.device_id,
            device_name=device_name or db_token.device_name,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        # Get the new token from database to link parent
        new_token_hash = security_service.hash_token(new_tokens["refresh_token"])
        new_db_token = await self.refresh_token_repo.get_by_token_hash(new_token_hash)

        if new_db_token:
            # Link parent for chain tracking
            await self.refresh_token_repo.update(new_db_token, {"parent_token_id": db_token.id})

        # Revoke old token (rotation)
        await self.refresh_token_repo.revoke_token(
            db_token.id, replaced_by_id=new_db_token.id if new_db_token else None
        )
        await self.redis.invalidate_token_cache(token_hash)

        logger.info(f"Refreshed token for user {user.id}, device: {device_id}")

        return {
            "access_token": new_tokens["access_token"],
            "refresh_token": new_tokens["refresh_token"],
            "token_type": "bearer",
        }

    async def logout_device(self, user_id: uuid.UUID, refresh_token: str) -> dict[str, str]:
        """Logout from a specific device by revoking its refresh token.

        Args:
            user_id: UUID of the user
            refresh_token: Refresh token to revoke

        Returns:
            Dictionary with success message

        Raises:
            NotFoundError: If token not found
            AuthorizationError: If token doesn't belong to user
        """
        token_hash = security_service.hash_token(refresh_token)
        db_token = await self.refresh_token_repo.get_by_token_hash(token_hash)

        if not db_token:
            raise NotFoundError("Token not found.")

        if db_token.user_id != user_id:
            raise AuthorizationError("Token does not belong to this user.")

        # Revoke the token
        await self.refresh_token_repo.revoke_token(db_token.id)
        await self.redis.invalidate_token_cache(token_hash)

        logger.info(f"User {user_id} logged out from device: {db_token.device_id}")

        return {"message": "Successfully logged out from this device."}

    async def logout_all_devices(self, user_id: uuid.UUID, except_token: str | None = None) -> dict[str, str]:
        """Logout from all devices by revoking all refresh tokens.

        Args:
            user_id: UUID of the user
            except_token: Optional refresh token to keep active (current device)

        Returns:
            Dictionary with success message and count of revoked tokens
        """
        except_token_id = None
        if except_token:
            token_hash = security_service.hash_token(except_token)
            db_token = await self.refresh_token_repo.get_by_token_hash(token_hash)
            if db_token and db_token.user_id == user_id:
                except_token_id = db_token.id

        # Revoke all user tokens
        revoked_count = await self.refresh_token_repo.revoke_all_user_tokens(
            user_id=user_id, except_token_id=except_token_id
        )

        # Note: Redis cache will be invalidated by the repository method
        # or will naturally expire

        logger.info(f"User {user_id} logged out from all devices. Revoked {revoked_count} tokens.")

        return {"message": f"Successfully logged out from all devices. Revoked {revoked_count} sessions."}

    async def _generate_and_save_code(self, email: str, type_prefix) -> str:
        """Generate and save verification code in Redis"""
        code = generate_verification_code()

        code_key = f"{type_prefix}:{email}"
        attempt_key = f"{type_prefix}_attempts:{email}"
        await self.redis.set(code_key, code, timedelta(minutes=15))
        await self.redis.set(attempt_key, 0, timedelta(minutes=15))

        return code

    async def _validate_code(self, email: str, input_code: str, type_prefix: str):
        """Validate verification code against Redis"""
        code_key = f"{type_prefix}:{email}"
        attempt_key = f"{type_prefix}_attempts:{email}"

        stored_code = await self.redis.get(code_key)

        if not stored_code:
            raise BusinessRuleError("Code invalid or expired.")

        if stored_code != input_code:
            attempts: int = await self.redis.increment(attempt_key)

            if attempts == 1:
                await self.redis.expire(code_key, timedelta(minutes=10))

            if attempts >= 3:
                await self.redis.delete(code_key, attempt_key)
                raise BusinessRuleError(
                    "Too many incorrect entries. Request a new code.",
                )

            remaining = 3 - attempts
            raise BusinessRuleError(
                f"Invalid code. Remaining attempts:{remaining}",
            )

        await self.redis.delete(code_key, attempt_key)
        return True

    async def verify_email(
        self,
        verify_data,
        device_id: str | None = None,
        device_name: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ):
        """Verify user's email using the verification code"""
        user = await self.user_repo.get_by_email(verify_data.email)
        if not user:
            raise NotFoundError("User not found.")

        await self._validate_code(verify_data.email, input_code=verify_data.code, type_prefix="verify")

        await self.user_repo.update(user, {"is_verified": True})

        return await self._create_token_pair(
            user=user,
            device_id=device_id,
            device_name=device_name,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    async def resend_verification_code(self, email: str):
        user = await self.user_repo.get_by_email(email)

        if not user:
            return {"message": "If your account is unverified, a code has been sent."}

        if user.is_verified:
            return {"message": "If your account is unverified, a code has been sent."}

        spam_key = f"resend_limit:{email}"
        is_spaming = await self.redis.get(spam_key)

        if is_spaming:
            raise BusinessRuleError(
                "Please wait 2 minutes before sending another code.",
            )

        code: str = await self._generate_and_save_code(email, type_prefix="verify")

        await self.redis.set(spam_key, 1, expire=timedelta(minutes=2))

        await email_service.send_verification_code(email, code, name="Runner")

        response = {"message": "Verification code sent to your email."}

        # DEBUG: Return code in response when email service is down
        if settings.DEBUG_RETURN_VERIFICATION_CODE:
            logger.warning(f"DEBUG MODE: Returning verification code in response for {email}")
            response["debug_code"] = code

        return response

    async def forgot_password(self, email: str) -> dict[str, str]:
        user = await self.user_repo.get_by_email(email)
        code = None
        if user:
            code = await self._generate_and_save_code(email, type_prefix="reset")
            await email_service.send_reset_password_code(email=email, code=code, name=user.full_name or "Runner")

        response: dict[str, str] = {"message": "Verification code sent to your email"}

        # DEBUG: Return code in response when email service is down
        if settings.DEBUG_RETURN_VERIFICATION_CODE and code:
            logger.warning(f"DEBUG MODE: Returning reset code in response for {email}")
            response["debug_code"] = code

        return response

    async def verify_reset_code(self, verify_data: VerifyResetCodeRequest):
        user = await self.user_repo.get_by_email(verify_data.email)
        if not user:
            raise NotFoundError("User not found.")

        await self._validate_code(email=verify_data.email, input_code=verify_data.code, type_prefix="reset")

        reset_token = security_service.create_access_token(
            subject=user.id, extra_data={"scope": "password_reset"}, expires_delta=timedelta(minutes=10)
        )

        return {"reset_token": reset_token, "token_type": "bearer"}

    async def reset_password(self, reset_data: ResetPasswordRequest):
        try:
            payload = jwt.decode(reset_data.reset_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

            if payload.get("scope") != "password_reset":
                raise AuthenticationError("Invalid token scope")

            user_id = payload.get("sub")

        except Exception:
            raise AuthenticationError("Invalid or expired reset token.")

        user = await self.user_repo.get(user_id)
        if not user:
            raise NotFoundError("User not found.")

        new_hashed_password = security_service.get_password_hash(reset_data.new_password)
        await self.user_repo.update(user, {"hashed_password": new_hashed_password})

        return {"message": "Your password has been changed successfully."}

    async def register_email(self, register_data):
        """Register user using email and password"""

        existing_user = await self.user_repo.get_by_email(register_data.email)
        if existing_user:
            raise BusinessRuleError("Email already registered.")

        hashed_password = security_service.get_password_hash(register_data.password)
        new_user = User(
            email=register_data.email,
            hashed_password=hashed_password,
            full_name=register_data.full_name,
            provider=AuthProviderEnum.EMAIL,
            is_active=True,
            is_verified=False,
        )
        await self.user_repo.create(new_user)

        code: str = await self._generate_and_save_code(register_data.email, type_prefix="verify")

        await email_service.send_verification_code(
            email=register_data.email,
            code=code,
            name=register_data.full_name or "Runner",
        )

        response = {"message": "Verification code sent to your email."}

        # DEBUG: Return code in response when email service is down
        if settings.DEBUG_RETURN_VERIFICATION_CODE:
            logger.warning(f"DEBUG MODE: Returning verification code in response for {register_data.email}")
            response["debug_code"] = code

        return response

    async def authenticate_email(
        self,
        login_data,
        device_id: str | None = None,
        device_name: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ):
        """Authenticate user using email and password"""

        error_message = "Invalid email or password."
        user = await self.user_repo.get_by_email(login_data.email)
        if not user:
            raise AuthenticationError(error_message)

        if not user or not user.hashed_password:
            raise AuthenticationError(error_message)

        if not security_service.verify_password(login_data.password, user.hashed_password):
            raise AuthenticationError(error_message)

        if not user.is_verified:
            raise AuthorizationError(
                "Your email is not verified, please check your inbox.",
            )

        if not user.is_active:
            raise AuthorizationError(
                "Your account is not active, please contact support.",
            )

        return await self._create_token_pair(
            user=user,
            device_id=device_id,
            device_name=device_name,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    async def authenticate_google(
        self,
        token: str,
        device_id: str | None = None,
        device_name: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ):
        """Authenticate user using Google OAuth2 token"""
        try:
            id_info = id_token.verify_oauth2_token(token, google_requests.Request(), settings.GOOGLE_CLIENT_ID)

            email = id_info.get("email")
            social_id = id_info.get("sub")
            name = id_info.get("name")
            picture = id_info.get("picture")

        except ValueError:
            raise AuthenticationError(
                "Invalid Google token",
            )

        user = await self.user_repo.get_by_email(email)

        if not user:
            new_user = User(
                email=email,
                social_id=social_id,
                full_name=name,
                profile_image=picture,
                provider=AuthProviderEnum.GOOGLE,
                is_active=True,
            )
            user = await self.user_repo.create(new_user)
        else:
            if not user.social_id:
                await self.user_repo.update(
                    user,
                    {
                        "social_id": social_id,
                        "provider": AuthProviderEnum.GOOGLE,
                    },
                )

        return await self._create_token_pair(
            user=user,
            device_id=device_id,
            device_name=device_name,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    async def authenticate_apple(
        self,
        token: str,
        device_id: str | None = None,
        device_name: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ):
        """Authenticate user using Apple Sign-In token"""
        try:
            apple_keys_url = "https://appleid.apple.com/auth/keys"
            async with httpx.AsyncClient() as client:
                response = await client.get(apple_keys_url)
            keys = response.json().get("keys")

            header = jwt.get_unverified_header(token)
            kid = header.get("kid")

            key_data = next((key for key in keys if key["kid"] == kid), None)
            if not key_data:
                raise AuthenticationError("Invalid Apple token: key not found.")

            jwk_client = PyJWKClient(apple_keys_url)
            signing_key = jwk_client.get_signing_key_from_jwt(token)

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=[
                    settings.APPLE_BUNDLE_ID,
                    settings.APPLE_SERVICE_ID,
                ],
                issuer="https://appleid.apple.com",
                options={"verify_exp": True},
            )

            email = payload.get("email")
            social_id = payload.get("sub")

        except Exception:
            raise AuthenticationError("Invalid Apple token.")

        if not social_id or not isinstance(social_id, str):
            raise AuthenticationError("Invalid Apple token: missing or invalid subject.")

        user = await self.user_repo.get_by_social_id(social_id=social_id, provider=AuthProviderEnum.APPLE)

        if not user:
            new_user = User(
                email=email,
                social_id=social_id,
                provider=AuthProviderEnum.APPLE,
                is_active=True,
                profile_image=None,
            )
            user = await self.user_repo.create(new_user)
        else:
            if not user.social_id:
                await self.user_repo.update(
                    user,
                    {
                        "social_id": social_id,
                        "provider": AuthProviderEnum.APPLE,
                    },
                )

        return await self._create_token_pair(
            user=user,
            device_id=device_id,
            device_name=device_name,
            user_agent=user_agent,
            ip_address=ip_address,
        )
