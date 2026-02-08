from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import Base


class BaseRepository[ModelType: Base]:
    def __init__(self, db: AsyncSession, model: type[ModelType]):
        self.db: AsyncSession = db
        self.model = model

    async def get(self, id: Any) -> ModelType | None:
        result = await self.db.get(self.model, id)
        return result

    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        statement = select(self.model).offset(skip).limit(limit)
        result = await self.db.scalars(statement)
        return result.all()

    async def create(self, obj_in: ModelType) -> ModelType:
        self.db.add(obj_in)
        await self.db.commit()
        await self.db.refresh(obj_in)
        return obj_in

    async def update(self, db_obj: ModelType, obj_in: dict | Any) -> ModelType:
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, id: Any) -> ModelType | None:
        db_obj = await self.db.get(self.model, id)
        if db_obj:
            await self.db.delete(db_obj)
            await self.db.commit()
        return db_obj
