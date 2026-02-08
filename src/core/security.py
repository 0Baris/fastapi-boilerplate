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
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

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
