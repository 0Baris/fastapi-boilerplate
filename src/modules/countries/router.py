"""Router for countries endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.modules.auth.dependencies import get_current_user
from src.modules.countries.schemas import CountryListResponse, CountryResponse
from src.modules.countries.service import CountryService
from src.modules.users.models import User

router = APIRouter()


@router.get(
    path="/",
    response_model=CountryListResponse,
    summary="Get all countries",
    description="Returns list of all countries with timezone information. Supports search by name.",
)
async def get_countries(
    search: str | None = Query(default=None, max_length=100, description="Search countries by name"),
    current_user: User = Depends(dependency=get_current_user),  # noqa: ARG001
) -> CountryListResponse:
    """
    Get all countries with their timezone info.

    Mobile app uses this endpoint to display country picker with flags.

    Args:
        search: Optional search term to filter countries by name (case-insensitive)

    Returns:
        List of countries with name, code, and timezone
    """
    service = CountryService()

    if search:
        filtered: list[CountryResponse] = service.search_countries(query=search)
        return CountryListResponse(countries=filtered, total=len(filtered))

    return service.get_all_countries()


@router.get(
    path="/{code}",
    response_model=CountryResponse,
    summary="Get country by code",
    description="Get single country information by ISO 3166-1 alpha-2 code.",
)
async def get_country(
    code: str,
    current_user: User = Depends(dependency=get_current_user),  # noqa: ARG001
) -> CountryResponse:
    """
    Get single country by code.

    Args:
        code: ISO 3166-1 alpha-2 country code (e.g., 'TR', 'US')

    Returns:
        Country with name, code, and timezone

    Raises:
        404: Country not found
    """
    service = CountryService()
    country: CountryResponse | None = service.get_country_by_code(code)

    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Country with code '{code}' not found",
        )

    return country
