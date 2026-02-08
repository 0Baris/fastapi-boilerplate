"""Schemas for countries module."""

from pydantic import Field

from src.core.schema import BaseSchema


class CountryResponse(BaseSchema):
    """Single country information."""

    name: str = Field(default=..., description="Country name (e.g., 'Turkey')")
    code: str = Field(default=..., description="ISO 3166-1 alpha-2 code (e.g., 'TR')")
    timezone: str = Field(default=..., description="Primary IANA timezone (e.g., 'Europe/Istanbul')")
    flag_url: str = Field(default=..., description="Country flag image URL from flagcdn.com")


class CountryListResponse(BaseSchema):
    """List of countries."""

    countries: list[CountryResponse]
    total: int = Field(default=..., description="Total number of countries")
