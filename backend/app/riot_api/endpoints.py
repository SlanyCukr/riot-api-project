"""Riot API endpoint definitions and routing information."""

from typing import Dict, List, Optional
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class Region(str, Enum):
    """Riot API regions for regional routing."""

    AMERICAS = "americas"
    ASIA = "asia"
    EUROPE = "europe"
    SEA = "sea"


class Platform(str, Enum):
    """Riot API platforms for platform routing."""

    BR1 = "br1"
    EUN1 = "eun1"
    EUW1 = "euw1"
    JP1 = "jp1"
    KR = "kr"
    LA1 = "la1"
    LA2 = "la2"
    NA1 = "na1"
    OC1 = "oc1"
    PH2 = "ph2"
    RU = "ru"
    SG2 = "sg2"
    TH2 = "th2"
    TR1 = "tr1"
    TW2 = "tw2"
    VN2 = "vn2"


class QueueType(str, Enum):
    """Common queue types for filtering."""

    RANKED_SOLO = "420"
    RANKED_FLEX = "440"
    NORMAL_BLIND = "400"
    NORMAL_DRAFT = "430"
    ARAM = "450"
    CLASH = "700"
    BOT_3V3 = "830"
    BOT_5V5 = "840"
    BOT_5V5_INTRO = "850"
    BOT_5V5_BEGINNER = "860"
    BOT_5V5_INTERMEDIATE = "870"


class GameMode(str, Enum):
    """Game modes."""

    CLASSIC = "CLASSIC"
    ARAM = "ARAM"
    TUTORIAL = "TUTORIAL"
    URF = "URF"
    DOOMBOTSTEEMO = "DOOMBOTSTEEMO"
    ASCENSION = "ASCENSION"
    FIRSTBLOOD = "FIRSTBLOOD"
    KINGPORO = "KINGPORO"
    SIEGE = "SIEGE"
    ASSASSINATE = "ASSASSINATE"
    ARSR = "ARSR"
    DARKSTAR = "DARKSTAR"
    STARGUARDIAN = "STARGUARDIAN"
    PROJECT = "PROJECT"
    GAMEMODEX = "GAMEMODEX"
    ODYSSEY = "ODYSSEY"
    NEXUSBLITZ = "NEXUSBLITZ"


class LeagueQueueType(str, Enum):
    """League queue types for ranked entries."""

    RANKED_SOLO_5X5 = "RANKED_SOLO_5x5"
    RANKED_FLEX_SR = "RANKED_FLEX_SR"
    RANKED_FLEX_TT = "RANKED_FLEX_TT"
    RANKED_TFT = "RANKED_TFT"
    RANKED_TFT_TURBO = "RANKED_TFT_TURBO"
    RANKED_TFT_DOUBLE_UP = "RANKED_TFT_DOUBLE_UP"


class RiotAPIEndpoints:
    """Riot API endpoint definitions and routing."""

    # Platform to region mapping
    PLATFORM_TO_REGION: Dict[Platform, Region] = {
        Platform.BR1: Region.AMERICAS,
        Platform.LA1: Region.AMERICAS,
        Platform.LA2: Region.AMERICAS,
        Platform.NA1: Region.AMERICAS,
        Platform.EUN1: Region.EUROPE,
        Platform.EUW1: Region.EUROPE,
        Platform.RU: Region.EUROPE,
        Platform.TR1: Region.EUROPE,
        Platform.JP1: Region.ASIA,
        Platform.KR: Region.ASIA,
        Platform.OC1: Region.SEA,
        Platform.PH2: Region.SEA,
        Platform.SG2: Region.SEA,
        Platform.TH2: Region.SEA,
        Platform.TW2: Region.SEA,
        Platform.VN2: Region.SEA,
    }

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

    def get_region_for_platform(self, platform: Platform) -> Region:
        """Get the corresponding region for a platform."""
        return self.PLATFORM_TO_REGION.get(platform, self.region)

    def get_base_url(self, region: Optional[Region] = None) -> str:
        """Get base URL for regional endpoints."""
        region = region or self.region
        return f"https://{region.value}.api.riotgames.com"

    def get_platform_url(self, platform: Optional[Platform] = None) -> str:
        """Get base URL for platform endpoints."""
        platform = platform or self.platform
        return f"https://{platform.value}.api.riotgames.com"

    # Account endpoints (Regional)
    def account_by_riot_id(
        self, game_name: str, tag_line: str, region: Optional[Region] = None
    ) -> str:
        """Get account by Riot ID endpoint."""
        base_url = self.get_base_url(region)
        return f"{base_url}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"

    def account_by_puuid(self, puuid: str, region: Optional[Region] = None) -> str:
        """Get account by PUUID endpoint."""
        base_url = self.get_base_url(region)
        return f"{base_url}/riot/account/v1/accounts/by-puuid/{puuid}"

    def active_shard(
        self, puuid: str, game: str = "lol", region: Optional[Region] = None
    ) -> str:
        """Get active shard by PUUID endpoint."""
        base_url = self.get_base_url(region)
        return (
            f"{base_url}/riot/account/v1/active-shards/by-game/{game}/by-puuid/{puuid}"
        )

    # Summoner endpoints (Platform)
    def summoner_by_name(
        self, summoner_name: str, platform: Optional[Platform] = None
    ) -> str:
        """Get summoner by name endpoint."""
        platform_url = self.get_platform_url(platform)
        return f"{platform_url}/lol/summoner/v4/summoners/by-name/{summoner_name}"

    def summoner_by_puuid(self, puuid: str, platform: Optional[Platform] = None) -> str:
        """Get summoner by PUUID endpoint."""
        platform_url = self.get_platform_url(platform)
        return f"{platform_url}/lol/summoner/v4/summoners/by-puuid/{puuid}"

    def summoner_by_id(
        self, summoner_id: str, platform: Optional[Platform] = None
    ) -> str:
        """Get summoner by ID endpoint."""
        platform_url = self.get_platform_url(platform)
        return f"{platform_url}/lol/summoner/v4/summoners/{summoner_id}"

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

    def match_timeline_by_id(
        self, match_id: str, region: Optional[Region] = None
    ) -> str:
        """Get match timeline by ID endpoint."""
        base_url = self.get_base_url(region)
        return f"{base_url}/lol/match/v5/matches/{match_id}/timeline"

    # League endpoints (Platform)
    def league_entries_by_summoner(
        self, summoner_id: str, platform: Optional[Platform] = None
    ) -> str:
        """Get league entries by summoner ID endpoint."""
        platform_url = self.get_platform_url(platform)
        return f"{platform_url}/lol/league/v4/entries/by-summoner/{summoner_id}"

    def league_entries_by_queue_tier_division(
        self,
        queue: LeagueQueueType,
        tier: str,
        division: str,
        page: int = 1,
        platform: Optional[Platform] = None,
    ) -> str:
        """Get league entries by queue, tier, and division endpoint."""
        platform_url = self.get_platform_url(platform)
        return f"{platform_url}/lol/league/v4/entries/{queue.value}/{tier}/{division}?page={page}"

    def league_grandmaster_by_queue(
        self, queue: LeagueQueueType, platform: Optional[Platform] = None
    ) -> str:
        """Get grandmaster league by queue endpoint."""
        platform_url = self.get_platform_url(platform)
        return f"{platform_url}/lol/league/v4/grandmasterleagues/by-queue/{queue.value}"

    def league_challenger_by_queue(
        self, queue: LeagueQueueType, platform: Optional[Platform] = None
    ) -> str:
        """Get challenger league by queue endpoint."""
        platform_url = self.get_platform_url(platform)
        return f"{platform_url}/lol/league/v4/challengerleagues/by-queue/{queue.value}"

    def league_master_by_queue(
        self, queue: LeagueQueueType, platform: Optional[Platform] = None
    ) -> str:
        """Get master league by queue endpoint."""
        platform_url = self.get_platform_url(platform)
        return f"{platform_url}/lol/league/v4/masterleagues/by-queue/{queue.value}"

    # Spectator endpoints (Platform)
    def active_game_by_summoner(
        self, summoner_id: str, platform: Optional[Platform] = None
    ) -> str:
        """Get active game by summoner ID endpoint."""
        platform_url = self.get_platform_url(platform)
        return f"{platform_url}/lol/spectator/v4/active-games/by-summoner/{summoner_id}"

    def featured_games(self, platform: Optional[Platform] = None) -> str:
        """Get featured games endpoint."""
        platform_url = self.get_platform_url(platform)
        return f"{platform_url}/lol/spectator/v4/featured-games"

    # Champion Mastery endpoints (Platform)
    def champion_mastery_by_summoner(
        self, summoner_id: str, platform: Optional[Platform] = None
    ) -> str:
        """Get all champion mastery entries by summoner ID endpoint."""
        platform_url = self.get_platform_url(platform)
        return f"{platform_url}/lol/champion-mastery/v4/champion-masteries/by-summoner/{summoner_id}"

    def champion_mastery_by_champion(
        self, summoner_id: str, champion_id: int, platform: Optional[Platform] = None
    ) -> str:
        """Get champion mastery by summoner ID and champion ID endpoint."""
        platform_url = self.get_platform_url(platform)
        return f"{platform_url}/lol/champion-mastery/v4/champion-masteries/by-summoner/{summoner_id}/by-champion/{champion_id}"

    def champion_mastery_top(
        self, summoner_id: str, count: int = 3, platform: Optional[Platform] = None
    ) -> str:
        """Get top champion mastery entries by summoner ID endpoint."""
        platform_url = self.get_platform_url(platform)
        return f"{platform_url}/lol/champion-mastery/v4/champion-masteries/by-summoner/{summoner_id}/top?count={count}"

    def champion_mastery_total_score(
        self, summoner_id: str, platform: Optional[Platform] = None
    ) -> str:
        """Get total champion mastery score by summoner ID endpoint."""
        platform_url = self.get_platform_url(platform)
        return (
            f"{platform_url}/lol/champion-mastery/v4/scores/by-summoner/{summoner_id}"
        )

    # LOL Status endpoints (Platform)
    def lol_status(self, platform: Optional[Platform] = None) -> str:
        """Get League of Legends status endpoint."""
        platform_url = self.get_platform_url(platform)
        return f"{platform_url}/lol/status/v4/platform-data"

    # Tournament endpoints (Regional)
    def tournament_codes(
        self, tournament_id: int, count: int = 1, region: Optional[Region] = None
    ) -> str:
        """Get tournament codes endpoint."""
        base_url = self.get_base_url(region)
        return f"{base_url}/lol/tournament/v5/codes?count={count}&tournamentId={tournament_id}"

    def tournament_info_by_code(
        self, tournament_code: str, region: Optional[Region] = None
    ) -> str:
        """Get tournament info by code endpoint."""
        base_url = self.get_base_url(region)
        return f"{base_url}/lol/tournament/v5/codes/{tournament_code}"

    def match_by_tournament_code(
        self, match_id: str, tournament_code: str, region: Optional[Region] = None
    ) -> str:
        """Get match by tournament code endpoint."""
        base_url = self.get_base_url(region)
        return f"{base_url}/lol/match/v5/matches/{match_id}/by-tournament-code/{tournament_code}"

    def create_provider(self, region: Optional[Region] = None) -> str:
        """Create tournament provider endpoint."""
        base_url = self.get_base_url(region)
        return f"{base_url}/lol/tournament/v5/providers"

    def create_tournament(self, region: Optional[Region] = None) -> str:
        """Create tournament endpoint."""
        base_url = self.get_base_url(region)
        return f"{base_url}/lol/tournament/v5/tournaments"


class RateLimitInfo:
    """Rate limit information for different endpoints."""

    # Rate limits per method (requests per time window)
    METHOD_LIMITS = {
        # Account endpoints
        "account": {"requests": 100, "window": 120},  # 100 requests per 2 minutes
        # Summoner endpoints
        "summoner": {"requests": 500, "window": 600},  # 500 requests per 10 minutes
        # Match endpoints
        "match": {"requests": 100, "window": 120},  # 100 requests per 2 minutes
        "match_timeline": {"requests": 50, "window": 120},  # 50 requests per 2 minutes
        # League endpoints
        "league": {"requests": 300, "window": 600},  # 300 requests per 10 minutes
        # Spectator endpoints
        "spectator": {"requests": 300, "window": 600},  # 300 requests per 10 minutes
        # Champion Mastery endpoints
        "champion_mastery": {
            "requests": 1000,
            "window": 3600,
        },  # 1000 requests per hour
        # Status endpoints
        "status": {"requests": 500, "window": 600},  # 500 requests per 10 minutes
    }

    # App-level rate limits
    APP_LIMITS = {
        "short": {"requests": 20, "window": 1},  # 20 requests per second
        "long": {"requests": 100, "window": 120},  # 100 requests per 2 minutes
    }

    @classmethod
    def get_method_limit(cls, endpoint_type: str) -> Dict[str, int]:
        """Get rate limit for a specific endpoint type."""
        return cls.METHOD_LIMITS.get(endpoint_type, cls.METHOD_LIMITS["match"])

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
