from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exception import NotFoundError
from src.modules.users.models import User
from src.modules.users.repository import UserRepository
from src.modules.users.schemas import UserUpdate


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def get_profile(self, user_id) -> User:
        user = await self.user_repo.get(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    async def update_profile(self, user_id, update_data: UserUpdate) -> User:
        user = await self.user_repo.get(user_id)
        if not user:
            raise NotFoundError("User not found")

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return user

        updated_user = await self.user_repo.update(user, update_dict)
        return updated_user

    async def delete_account(self, user_id) -> None:
        user = await self.user_repo.get(user_id)
        if not user:
            raise NotFoundError("User not found")

        # Deactivate user account (user can no longer log in)
        # To implement true soft delete with timestamp, add deleted_at field to User model
        await self.user_repo.update(user, {"is_active": False})
