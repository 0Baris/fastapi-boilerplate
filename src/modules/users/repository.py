"""User repository for authentication and user management."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import AuthProviderEnum
from src.core.repository import BaseRepository
from src.modules.users.models import User


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, User)

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address.

        Args:
            email: User's email address

        Returns:
            User if found, None otherwise
        """
        statement = select(self.model).where(self.model.email == email)
        result = await self.db.scalar(statement)
        return result

    async def get_by_social_id(self, social_id: str, provider: AuthProviderEnum) -> User | None:
        """Get user by social ID and provider.

        Args:
            social_id: Social provider user ID
            provider: Auth provider (GOOGLE, APPLE, etc.)

        Returns:
            User if found, None otherwise
        """
        statement = select(self.model).where(self.model.provider == provider).where(self.model.social_id == social_id)
        result = await self.db.scalar(statement)
        return result
