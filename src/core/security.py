import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Union

import jwt
from passlib.context import CryptContext

from src.core.config import settings


class SecurityService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key: str = settings.SECRET_KEY
        self.algorithm: str = settings.ALGORITHM
        self.access_token_expire_minutes: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    def create_access_token(
        self, subject: Union[str, Any], expires_delta: timedelta | None = None, extra_data: dict[str, Any] | None = None
    ) -> str:
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire: datetime = datetime.now(UTC) + timedelta(minutes=self.access_token_expire_minutes)
        to_encode = {"sub": str(subject), "exp": expire}
        if extra_data:
            to_encode.update(extra_data)
        # `kid` lets the verifier pick the correct signing key during a key
        # rotation window (see decode_access_token).
        return jwt.encode(
            to_encode,
            self.secret_key,
            algorithm=self.algorithm,
            headers={"kid": settings.JWT_KEY_ID},
        )

    def decode_access_token(self, token: str) -> dict[str, Any]:
        """Decode + verify a JWT, supporting current + grace-period old key.

        New tokens carry a `kid` header. During a key rotation:
        - current `kid` (or no `kid`, for pre-rotation tokens) → verify with SECRET_KEY.
        - old `kid` → verify with JWT_OLD_KEY while JWT_OLD_KEY_VALID_UNTIL is in the future.
        Unknown kid / expired grace → InvalidTokenError.
        """
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        if kid == settings.JWT_KEY_ID or not kid:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

        if kid == settings.JWT_OLD_KEY_ID and settings.JWT_OLD_KEY and self._old_key_still_valid():
            return jwt.decode(token, settings.JWT_OLD_KEY, algorithms=[self.algorithm])

        raise jwt.InvalidTokenError(f"Unknown or expired JWT key id: {kid!r}")

    def _old_key_still_valid(self) -> bool:
        until_raw = settings.JWT_OLD_KEY_VALID_UNTIL
        if not until_raw:
            return False
        try:
            until = datetime.fromisoformat(until_raw)
        except ValueError:
            return False
        if until.tzinfo is None:
            until = until.replace(tzinfo=UTC)
        return datetime.now(UTC) < until

    def prehash_password(self, password: str) -> str:
        """SHA-256 ile ön hashleme yaparak bcrypt 72 bayt limitini aşar."""
        sha256_hash: bytes = hashlib.sha256(password.encode()).digest()
        return base64.b64encode(sha256_hash).decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        prehashed: str = self.prehash_password(plain_password)
        return self.pwd_context.verify(prehashed, hashed_password)

    def get_password_hash(self, password: str) -> str:
        prehashed: str = self.prehash_password(password)
        return self.pwd_context.hash(prehashed)

    def create_refresh_token(self) -> str:
        """Generate cryptographically secure random refresh token."""
        return secrets.token_urlsafe(32)

    def hash_token(self, token: str) -> str:
        """Hash token using SHA-256 before storing in database."""
        return hashlib.sha256(token.encode()).hexdigest()

    def verify_token_hash(self, token: str, token_hash: str) -> bool:
        """Verify token against stored hash."""
        return self.hash_token(token) == token_hash


security_service: SecurityService = SecurityService()
