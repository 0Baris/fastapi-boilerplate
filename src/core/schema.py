from datetime import datetime
from enum import Enum, IntEnum
from typing import Annotated

from fastapi import Path
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
)

ObjectIdKey = Annotated[str, BeforeValidator(str)]
ObjectIdValue = Field(alias="_id")
ObjectIdPath = Annotated[str, Path(min_length=24, max_length=24)]

UuidKey = Annotated[str, BeforeValidator(str)]


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    @field_serializer("*", mode="wrap", when_used="unless-none")
    def serialize_datetime(self, value, handler, info):
        """Custom serializer for datetime objects and enums"""
        result = handler(value)
        if isinstance(result, datetime):
            return result.timestamp()
        elif isinstance(result, Enum):
            return result.value
        return result


class Size(IntEnum):
    SIZE_10 = 10
    SIZE_25 = 25
    SIZE_50 = 50
    SIZE_100 = 100
    SIZE_250 = 250
    SIZE_500 = 500


class PaginationIn(BaseModel):
    page: int = 1
    size: Size = Size.SIZE_25

    @field_validator("size", mode="before")
    def parse_size(cls, v):
        if isinstance(v, int):
            size_mapping = {
                25: Size.SIZE_25,
                50: Size.SIZE_50,
                100: Size.SIZE_100,
                250: Size.SIZE_250,
                500: Size.SIZE_500,
            }
            if v in size_mapping:
                return size_mapping[v]
            else:
                return Size.SIZE_25
        return v

    @property
    def offset(self) -> int:
        if self.page < 1:
            self.page = 1
        return (self.page - 1) * self.size.value


class PaginationOut[T](BaseSchema):
    total: int = 0
    items: list[T] = []
    page: int = 1
    size: int = 25


class AllEnum(str, Enum):
    ALL = "all"


class AnyEnum(str, Enum):
    ANY = "any"


class ErrorResponse(BaseModel):
    detail: str
