"""Timezone utilities for user timezone management.

This module provides utilities for:
- Inferring timezone from GPS coordinates
- Inferring timezone from country code
- Validating timezone strings
- Getting current time in user's timezone
"""

from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo, available_timezones

from timezonefinder import TimezoneFinder

from src.core.logging import get_logger

logger = get_logger(__name__)

_tf_instance: TimezoneFinder | None = None


@lru_cache(maxsize=1)
def _get_country_timezone_mapping() -> dict[str, str]:
    """Get or create country code to timezone mapping.

    Uses pytz to map ISO 3166-1 alpha-2 country codes to their primary timezone.
    Results are cached after first call.

    Returns:
        Dict mapping country codes to primary timezone strings
    """
    try:
        # Manual mapping of country codes to their primary/capital timezones
        # This is a simplified version - for production, you might want a more comprehensive mapping
        mapping: dict[str, str] = {
            # Europe
            "TR": "Europe/Istanbul",
            "GB": "Europe/London",
            "FR": "Europe/Paris",
            "DE": "Europe/Berlin",
            "IT": "Europe/Rome",
            "ES": "Europe/Madrid",
            "NL": "Europe/Amsterdam",
            "BE": "Europe/Brussels",
            "CH": "Europe/Zurich",
            "AT": "Europe/Vienna",
            "SE": "Europe/Stockholm",
            "NO": "Europe/Oslo",
            "DK": "Europe/Copenhagen",
            "FI": "Europe/Helsinki",
            "PL": "Europe/Warsaw",
            "GR": "Europe/Athens",
            "PT": "Europe/Lisbon",
            "IE": "Europe/Dublin",
            "CZ": "Europe/Prague",
            "HU": "Europe/Budapest",
            "RO": "Europe/Bucharest",
            "BG": "Europe/Sofia",
            "HR": "Europe/Zagreb",
            "UA": "Europe/Kiev",
            "RU": "Europe/Moscow",
            # Americas
            "US": "America/New_York",
            "CA": "America/Toronto",
            "MX": "America/Mexico_City",
            "BR": "America/Sao_Paulo",
            "AR": "America/Argentina/Buenos_Aires",
            "CL": "America/Santiago",
            "CO": "America/Bogota",
            "PE": "America/Lima",
            "VE": "America/Caracas",
            # Asia
            "CN": "Asia/Shanghai",
            "JP": "Asia/Tokyo",
            "IN": "Asia/Kolkata",
            "KR": "Asia/Seoul",
            "ID": "Asia/Jakarta",
            "TH": "Asia/Bangkok",
            "VN": "Asia/Ho_Chi_Minh",
            "PH": "Asia/Manila",
            "MY": "Asia/Kuala_Lumpur",
            "SG": "Asia/Singapore",
            "HK": "Asia/Hong_Kong",
            "TW": "Asia/Taipei",
            "PK": "Asia/Karachi",
            "BD": "Asia/Dhaka",
            "AE": "Asia/Dubai",
            "SA": "Asia/Riyadh",
            "IL": "Asia/Jerusalem",
            # Oceania
            "AU": "Australia/Sydney",
            "NZ": "Pacific/Auckland",
            # Africa
            "ZA": "Africa/Johannesburg",
            "EG": "Africa/Cairo",
            "NG": "Africa/Lagos",
            "KE": "Africa/Nairobi",
            "MA": "Africa/Casablanca",
        }

        logger.info(f"Loaded timezone mapping for {len(mapping)} countries")
        return mapping

    except Exception as e:
        logger.error(f"Error loading country timezone mapping: {e}")
        return {}


def get_timezone_finder() -> TimezoneFinder:
    """Get or create singleton TimezoneFinder instance.

    TimezoneFinder is expensive to instantiate, so we create it once and reuse.

    Returns:
        TimezoneFinder instance
    """
    global _tf_instance
    if _tf_instance is None:
        _tf_instance = TimezoneFinder()
        logger.info("Initialized TimezoneFinder instance")
    return _tf_instance


def infer_timezone_from_location(latitude: float, longitude: float) -> str:
    """Infer IANA timezone string from GPS coordinates.

    Uses timezonefinder library which has 99.9% accuracy for valid coordinates.

    Args:
        latitude: Latitude in decimal degrees (-90 to 90)
        longitude: Longitude in decimal degrees (-180 to 180)

    Returns:
        IANA timezone string (e.g., "Europe/Istanbul", "America/New_York")
        Returns "UTC" if timezone cannot be determined

    Example:
        >>> infer_timezone_from_location(41.0082, 28.9784)
        'Europe/Istanbul'
        >>> infer_timezone_from_location(40.7128, -74.0060)
        'America/New_York'
    """
    try:
        if not (-90 <= latitude <= 90):
            logger.warning(f"Invalid latitude: {latitude}, using UTC")
            return "UTC"
        if not (-180 <= longitude <= 180):
            logger.warning(f"Invalid longitude: {longitude}, using UTC")
            return "UTC"

        tf = get_timezone_finder()
        tz_name = tf.timezone_at(lat=latitude, lng=longitude)

        if tz_name:
            logger.debug(f"Inferred timezone {tz_name} from coordinates ({latitude}, {longitude})")
            return tz_name

        logger.warning(f"Could not infer timezone from coordinates ({latitude}, {longitude}), using UTC")
        return "UTC"

    except Exception as e:
        logger.error(f"Error inferring timezone from location: {e}", exc_info=True)
        return "UTC"


def infer_timezone_from_country(country_code: str) -> str:
    """Infer timezone from ISO 3166-1 alpha-2 country code.

    Uses country_timezone library to map country code to primary timezone.
    Results are cached for performance.

    Args:
        country_code: ISO 3166-1 alpha-2 country code (e.g., "TR", "US", "GB")

    Returns:
        IANA timezone string (e.g., "Europe/Istanbul")
        Returns "UTC" if country not found

    Example:
        >>> infer_timezone_from_country("TR")
        'Europe/Istanbul'
        >>> infer_timezone_from_country("US")
        'America/New_York'
    """
    try:
        country_upper = country_code.upper() if country_code else ""
        mapping = _get_country_timezone_mapping()
        tz_name = mapping.get(country_upper, "UTC")

        if tz_name != "UTC":
            logger.debug(f"Inferred timezone {tz_name} from country code {country_upper}")

        return tz_name

    except Exception as e:
        logger.error(f"Error inferring timezone from country: {e}", exc_info=True)
        return "UTC"


def validate_timezone(tz_string: str) -> bool:
    """Validate if a string is a valid IANA timezone identifier.

    Args:
        tz_string: Timezone string to validate (e.g., "Europe/Istanbul")

    Returns:
        True if valid IANA timezone, False otherwise

    Example:
        >>> validate_timezone("Europe/Istanbul")
        True
        >>> validate_timezone("Invalid/Timezone")
        False
    """
    try:
        if not tz_string:
            return False

        # Check if timezone exists in zoneinfo database
        if tz_string in available_timezones():
            return True

        # Try to create ZoneInfo object
        ZoneInfo(tz_string)
        return True

    except Exception:
        return False


def get_user_current_time(tz_string: str) -> datetime:
    """Get current datetime in user's timezone.

    Args:
        tz_string: IANA timezone string (e.g., "Europe/Istanbul")

    Returns:
        Current datetime in user's timezone (timezone-aware)
        Returns UTC time if timezone is invalid

    Example:
        >>> dt = get_user_current_time("Europe/Istanbul")
        >>> dt.tzinfo
        ZoneInfo(key='Europe/Istanbul')
        >>> dt.hour  # Current hour in Istanbul time
        14
    """
    try:
        if not validate_timezone(tz_string):
            logger.warning(f"Invalid timezone {tz_string}, using UTC")
            tz_string = "UTC"

        user_tz = ZoneInfo(tz_string)
        return datetime.now(tz=user_tz)

    except Exception as e:
        logger.error(f"Error getting user current time: {e}", exc_info=True)
        return datetime.now(tz=ZoneInfo("UTC"))
