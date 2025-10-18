"""
Service layer utility functions.

This module provides common utility functions used across different services
to eliminate code duplication and ensure consistency.
"""

import re
from typing import Optional, Set
import structlog

logger = structlog.get_logger(__name__)

# Valid Riot API platform codes
VALID_PLATFORMS: Set[str] = {
    "NA1",  # North America
    "BR1",  # Brazil
    "EUW1",  # Europe West
    "EUN1",  # Europe Nordic & East
    "JP1",  # Japan
    "KR",  # Korea
    "LA1",  # Latin America North
    "LA2",  # Latin America South
    "OC1",  # Oceania
    "TR1",  # Turkey
    "RU",  # Russia
    "PH2",  # Philippines
    "SG2",  # Singapore
    "TH2",  # Thailand
    "TW2",  # Taiwan
    "VN2",  # Vietnam
}

# Platform region mapping
PLATFORM_REGIONS: dict[str, str] = {
    "NA1": "americas",
    "BR1": "americas",
    "LA1": "americas",
    "LA2": "americas",
    "OC1": "americas",
    "EUW1": "europe",
    "EUN1": "europe",
    "TR1": "europe",
    "RU": "europe",
    "KR": "asia",
    "JP1": "asia",
    "PH2": "sea",  # Southeast Asia
    "SG2": "sea",
    "TH2": "sea",
    "TW2": "sea",
    "VN2": "sea",
}


def validate_platform(platform: str) -> str:
    """
    Validate and normalize a Riot API platform code.

    Args:
        platform: Platform code to validate (e.g., "na1", "NA1", "na1 ")

    Returns:
        Normalized platform code in uppercase format

    Raises:
        ValueError: If platform is invalid or unsupported

    Examples:
        >>> validate_platform("na1")
        'NA1'
        >>> validate_platform("EUW1")
        'EUW1'
    """
    if not platform:
        raise ValueError("Platform cannot be empty or None")

    # Clean and normalize platform input
    normalized_platform = platform.strip().upper()

    if normalized_platform not in VALID_PLATFORMS:
        valid_platforms_str = ", ".join(sorted(VALID_PLATFORMS))
        raise ValueError(
            f"Invalid platform '{platform}'. Valid platforms are: {valid_platforms_str}"
        )

    logger.debug(
        "Platform validated and normalized",
        input_platform=platform,
        normalized_platform=normalized_platform,
    )

    return normalized_platform


def get_platform_region(platform: str) -> str:  # noqa: F401 - Useful for future regional API calls
    """
    Get the regional shard for a given platform.

    Args:
        platform: Valid platform code

    Returns:
        Region string ('americas', 'europe', 'asia', 'sea')

    Raises:
        ValueError: If platform is invalid
    """
    normalized_platform = validate_platform(platform)

    region = PLATFORM_REGIONS.get(normalized_platform)
    if not region:
        raise ValueError(f"No region mapping found for platform: {normalized_platform}")

    logger.debug(
        "Platform region retrieved",
        platform=normalized_platform,
        region=region,
    )

    return region


def is_valid_platform(platform: str) -> bool:  # noqa: F401 - Useful for conditional validation without exceptions
    """
    Check if a platform code is valid without raising an exception.

    Args:
        platform: Platform code to check

    Returns:
        True if platform is valid, False otherwise
    """
    try:
        validate_platform(platform)
        return True
    except ValueError:
        return False


def sanitize_string_field(
    value: Optional[str], max_length: Optional[int] = None
) -> Optional[str]:
    """
    Sanitize a string field by removing extra whitespace and validating length.

    Args:
        value: String value to sanitize
        max_length: Maximum allowed length (None for no limit)

    Returns:
        Sanitized string or None if input is None/empty

    Raises:
        ValueError: If string exceeds max_length
    """
    if value is None:
        return None

    # Remove leading/trailing whitespace and normalize internal whitespace
    sanitized = re.sub(r"\s+", " ", value.strip())

    if not sanitized:
        return None

    if max_length and len(sanitized) > max_length:
        raise ValueError(f"String exceeds maximum length of {max_length} characters")

    return sanitized


def validate_puuid(puuid: str) -> str:
    """
    Validate a Riot API PUUID format.

    Args:
        puuid: PUUID string to validate

    Returns:
        Normalized PUUID

    Raises:
        ValueError: If PUUID format is invalid
    """
    if not puuid:
        raise ValueError("PUUID cannot be empty or None")

    # Remove whitespace and validate format
    normalized_puuid = puuid.strip()

    # PUUIDs should be 78 character alphanumeric strings (with dashes)
    # Riot API PUUID format: 8-4-4-4-12 characters with dashes
    puuid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
    )

    if not puuid_pattern.match(normalized_puuid):
        raise ValueError(
            f"Invalid PUUID format: '{puuid}'. "
            "PUUID should be in format: 12345678-1234-1234-1234-123456789012"
        )

    return normalized_puuid.lower()


def validate_summoner_name(summoner_name: str) -> str:
    """
    Validate and normalize a summoner name.

    Args:
        summoner_name: Summoner name to validate

    Returns:
        Normalized summoner name

    Raises:
        ValueError: If summoner name is invalid
    """
    if not summoner_name:
        raise ValueError("Summoner name cannot be empty or None")

    # Remove extra whitespace but preserve internal spacing
    normalized = sanitize_string_field(summoner_name, max_length=16)

    if not normalized:
        raise ValueError("Summoner name cannot be empty or whitespace only")

    # Basic validation - summoner names typically contain alphanumeric characters and spaces
    if not re.match(r"^[\w\s]+$", normalized):
        raise ValueError(
            f"Invalid summoner name: '{summoner_name}'. "
            "Summoner names should only contain letters, numbers, underscores, and spaces"
        )

    return normalized


def create_safe_riot_id(
    riot_id: Optional[str], tag_line: Optional[str]
) -> Optional[str]:
    """
    Create a safe Riot ID display string from riot_id and tag_line.

    Args:
        riot_id: Riot ID game name
        tag_line: Riot ID tagline

    Returns:
        Combined Riot ID string in format "name#tag" or None if both are None/empty
    """
    safe_riot_id = sanitize_string_field(riot_id)
    safe_tag_line = sanitize_string_field(tag_line)

    if safe_riot_id and safe_tag_line:
        return f"{safe_riot_id}#{safe_tag_line}"
    elif safe_riot_id:
        return safe_riot_id
    else:
        return None


