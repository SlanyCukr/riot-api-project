"""Riot API endpoint definitions and routing information."""

from typing import Dict, List, Optional
import structlog

from .constants import Region, Platform, QueueType

logger = structlog.get_logger(__name__)


class RiotAPIEndpoints:
    """Riot API endpoint definitions and routing."""

    def __init__(
        self, region: Region = Region.EUROPE, platform: Platform = Platform.EUN1
    ):
        """
        Initialize endpoint configuration.

        Args:
            region: Default region for regional endpoints
            platform: Default platform for platform endpoints
        """
        self.region = region
        self.platform = platform

    def get_base_url(self, region: Optional[Region] = None) -> str:
        """Get base URL for regional endpoints."""
        region = region or self.region
        # Handle both Region enum and string
        region_str = region.value if isinstance(region, Region) else region
        return f"https://{region_str}.api.riotgames.com"

    def get_platform_url(self, platform: Optional[Platform] = None) -> str:
        """Get base URL for platform endpoints."""
        platform = platform or self.platform
        # Handle both Platform enum and string
        platform_str = platform.value if isinstance(platform, Platform) else platform
        return f"https://{platform_str}.api.riotgames.com"

    # Account endpoints (Regional)
    def account_by_riot_id(
        self, game_name: str, tag_line: str, region: Optional[Region] = None
    ) -> str:
        """Get account by Riot ID endpoint."""
        base_url = self.get_base_url(region)
        return f"{base_url}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"

    def summoner_by_puuid(self, puuid: str, platform: Optional[Platform] = None) -> str:
        """Get summoner by PUUID endpoint."""
        platform_url = self.get_platform_url(platform)
        return f"{platform_url}/lol/summoner/v4/summoners/by-puuid/{puuid}"

    # Match endpoints (Regional)
    def match_list_by_puuid(
        self,
        puuid: str,
        start: int = 0,
        count: int = 20,
        queue: Optional[QueueType] = None,
        type: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        region: Optional[Region] = None,
    ) -> str:
        """Get match list by PUUID endpoint."""
        base_url = self.get_base_url(region)
        url = f"{base_url}/lol/match/v5/matches/by-puuid/{puuid}/ids"

        params: list[str] = []
        params.append(f"start={start}")
        params.append(f"count={count}")

        if queue:
            params.append(f"queue={queue.value}")
        if type:
            params.append(f"type={type}")
        if start_time:
            params.append(f"startTime={start_time}")
        if end_time:
            params.append(f"endTime={end_time}")

        return f"{url}?{'&'.join(params)}"

    def match_by_id(self, match_id: str, region: Optional[Region] = None) -> str:
        """Get match by ID endpoint."""
        base_url = self.get_base_url(region)
        return f"{base_url}/lol/match/v5/matches/{match_id}"

    # League endpoints (Platform)
    def league_entries_by_puuid(
        self, puuid: str, platform: Optional[Platform] = None
    ) -> str:
        """Get league entries by PUUID endpoint."""
        platform_url = self.get_platform_url(platform)
        return f"{platform_url}/lol/league/v4/entries/by-puuid/{puuid}"


class RateLimitInfo:
    """Rate limit information for different endpoints."""

    # App-level rate limits
    APP_LIMITS = {
        "short": {"requests": 20, "window": 1},  # 20 requests per second
        "long": {"requests": 100, "window": 120},  # 100 requests per 2 minutes
    }

    @classmethod
    def get_app_limits(cls) -> Dict[str, Dict[str, int]]:
        """Get app-level rate limits."""
        return cls.APP_LIMITS


def parse_rate_limit_header(header_value: str) -> List[Dict[str, int]]:
    """
    Parse rate limit header value.

    Example: "20:1,100:120" -> [{"requests": 20, "window": 1}, {"requests": 100, "window": 120}]

    Args:
        header_value: Rate limit header value

    Returns:
        List of rate limit dictionaries
    """
    if not header_value:
        return []

    limits: list[dict[str, int]] = []
    for part in header_value.split(","):
        try:
            requests, window = map(int, part.strip().split(":"))
            limits.append({"requests": requests, "window": window})
        except (ValueError, AttributeError):
            logger.warning(
                "Failed to parse rate limit part", part=part, header=header_value
            )
            continue

    return limits


def parse_rate_count_header(header_value: str) -> List[Dict[str, int]]:
    """
    Parse rate count header value.

    Example: "15:1,80:120" -> [{"requests": 15, "window": 1}, {"requests": 80, "window": 120}]

    Args:
        header_value: Rate count header value

    Returns:
        List of rate count dictionaries
    """
    return parse_rate_limit_header(header_value)
