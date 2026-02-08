"""Service for managing country data."""

import csv
from csv import DictReader
from pathlib import Path

from src.core.logging import get_logger
from src.modules.countries.schemas import CountryListResponse, CountryResponse

logger = get_logger(__name__)

_countries_cache: CountryListResponse | None = None


def initialize_countries_cache() -> None:
    """
    Initialize countries cache at application startup.

    This prevents blocking I/O during request validation by pre-loading
    all country data into memory (~25KB).

    Called by FastAPI lifespan event in main.py.
    """
    global _countries_cache

    if _countries_cache is not None:
        logger.info("Countries cache already initialized")
        return

    logger.info("Initializing countries cache at startup...")
    service = CountryService()
    _ = service.get_all_countries()  # This will populate _countries_cache
    logger.info(f"Countries cache initialized with {_countries_cache.total if _countries_cache else 0} countries")


def get_country_by_code_cached(code: str) -> CountryResponse | None:
    """
    Get country by code from cache (no I/O, safe for validators).

    This function accesses the pre-loaded cache without triggering file I/O,
    making it safe to call from Pydantic validators.

    Args:
        code: ISO 3166-1 alpha-2 country code (e.g., 'TR', 'US')

    Returns:
        Country if found in cache, None if cache not initialized or country not found
    """
    global _countries_cache

    if _countries_cache is None:
        logger.warning(msg="Countries cache not initialized - validation may fail")
        return None

    code_upper: str = code.upper()

    for country in _countries_cache.countries:
        if country.code == code_upper:
            return country

    return None


class CountryService:
    """Service for managing country data."""

    @staticmethod
    def _get_csv_path() -> Path:
        """Get path to countries CSV file."""
        return Path(__file__).parent / "data" / "countries.csv"

    def get_all_countries(self) -> CountryListResponse:
        """
        Get all countries with timezone mapping.

        Cached in memory after first call (~25KB data).

        Returns:
            CountryListResponse with all countries sorted by name
        """
        global _countries_cache

        if _countries_cache is not None:
            return _countries_cache

        countries = []
        csv_path: Path = self._get_csv_path()

        logger.info(f"Loading countries from {csv_path}")

        with csv_path.open(encoding="utf-8") as f:
            reader: DictReader[str] = csv.DictReader(f)
            for row in reader:
                name: str = row["Name"]
                code: str = row["Code"]
                timezone: str = row.get("Timezone", "UTC")

                flag_url = f"https://flagcdn.com/w320/{code.lower()}.png"

                countries.append(CountryResponse(name=name, code=code, timezone=timezone, flag_url=flag_url))

        countries.sort(key=lambda x: x.name)

        logger.info(f"Loaded {len(countries)} countries")

        _countries_cache = CountryListResponse(countries=countries, total=len(countries))

        return _countries_cache

    def search_countries(self, query: str) -> list[CountryResponse]:
        """
        Search countries by name (case-insensitive).

        Args:
            query: Search term

        Returns:
            List of matching countries
        """
        all_data: CountryListResponse = self.get_all_countries()
        query_lower: str = query.lower()

        filtered: list[CountryResponse] = [
            country for country in all_data.countries if query_lower in country.name.lower()
        ]

        logger.debug(f"Search '{query}' found {len(filtered)} countries")

        return filtered

    def get_country_by_code(self, code: str) -> CountryResponse | None:
        """
        Get single country by ISO code.

        Args:
            code: ISO 3166-1 alpha-2 country code (e.g., 'TR', 'US')

        Returns:
            Country if found, None otherwise
        """
        all_data: CountryListResponse = self.get_all_countries()
        code_upper: str = code.upper()

        for country in all_data.countries:
            if country.code == code_upper:
                return country

        return None
