"""Riot API HTTP client with proper rate limiting, error handling, and authentication."""

import asyncio
from typing import Optional, Dict, Any, List, Union, Callable
import aiohttp
import structlog

from ..config import get_global_settings
from .rate_limiter import RateLimiter
from .errors import (
    RiotAPIError,
    RateLimitError,
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
    BadRequestError,
)
from .models import (
    AccountDTO,
    SummonerDTO,
    MatchListDTO,
    MatchDTO,
    LeagueEntryDTO,
)
from .endpoints import RiotAPIEndpoints
from .constants import Region, Platform, QueueType

logger = structlog.get_logger(__name__)


class RiotAPIClient:
    """Comprehensive Riot API client with rate limiting and error handling."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        region: Optional[Region] = None,
        platform: Optional[Platform] = None,
        enable_logging: bool = True,
        request_callback: Optional[Callable[[str, int], None]] = None,
    ):
        """
        Initialize Riot API client.

        Args:
            api_key: Riot API key (uses config if None)
            region: Default region for regional endpoints
            platform: Default platform for platform endpoints
            enable_logging: Enable request/response logging
        """
        settings = get_global_settings()
        self.api_key = api_key or settings.riot_api_key
        self.region = region or Region(settings.riot_region.lower())
        self.platform = platform or Platform(settings.riot_platform.lower())
        self.enable_logging = enable_logging
        self.request_callback = request_callback

        # Initialize components
        self.rate_limiter = RateLimiter()
        self.endpoints = RiotAPIEndpoints(self.region, self.platform)

        # HTTP session
        self.session = None
        self._session_lock = asyncio.Lock()

        # Statistics
        self.stats = {
            "requests_made": 0,
            "retries": 0,
            "errors": 0,
        }

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_session()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Async context manager exit."""
        await self.close()

    async def start_session(self) -> None:
        """Start the aiohttp session."""
        if self.session is None or self.session.closed:
            async with self._session_lock:
                if self.session is None or self.session.closed:
                    headers = {
                        "X-Riot-Token": self.api_key,
                        "Content-Type": "application/json",
                        "User-Agent": "RiotAPI-SmurfDetector/1.0",
                    }

                    timeout = aiohttp.ClientTimeout(total=30)
                    connector = aiohttp.TCPConnector(
                        limit=20,
                        limit_per_host=5,
                        ttl_dns_cache=300,
                        use_dns_cache=True,
                    )

                    self.session = aiohttp.ClientSession(
                        headers=headers, timeout=timeout, connector=connector
                    )

                    # Handle both enum and string types for logging
                    region_str = (
                        self.region.value
                        if isinstance(self.region, Region)
                        else self.region
                    )
                    platform_str = (
                        self.platform.value
                        if isinstance(self.platform, Platform)
                        else self.platform
                    )

                    logger.info(
                        "Riot API client session started",
                        region=region_str,
                        platform=platform_str,
                        api_key_prefix="[REDACTED]" if self.api_key else "None",
                    )

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("Riot API client session closed")

    async def _make_request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        retry_on_failure: bool = True,
    ) -> Any:
        """
        Make HTTP request with rate limiting and retry logic.

        Args:
            url: Request URL
            method: HTTP method
            params: Query parameters
            data: Request body data
            retry_on_failure: Retry on transient failures

        Returns:
            Response data as dictionary or list

        Raises:
            RiotAPIError: For API errors
        """
        await self.start_session()

        if self.session is None:
            raise RiotAPIError("Session not initialized")

        # Rate limiting
        endpoint_path = self._extract_endpoint_path(url)
        await self.rate_limiter.wait_if_needed(endpoint_path, method)

        # Simplified retry logic
        max_retries = 3 if retry_on_failure else 0
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                self.stats["requests_made"] += 1
                if self.request_callback:
                    self.request_callback("requests_made", 1)

                async with self.session.request(
                    method, url, params=params, json=data
                ) as response:
                    self.rate_limiter.update_limits(
                        dict(response.headers), endpoint_path, method
                    )

                    # Handle status codes
                    if response.status == 400:
                        raise BadRequestError("Invalid request parameters")
                    elif response.status == 401:
                        raise AuthenticationError("Invalid API key")
                    elif response.status == 403:
                        raise ForbiddenError("Access forbidden")
                    elif response.status == 404:
                        raise NotFoundError("Resource not found")
                    elif response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", 1))
                        if attempt < max_retries:
                            await asyncio.sleep(retry_after)
                            self.stats["retries"] += 1
                            continue
                        raise RateLimitError(
                            "Rate limit exceeded", retry_after=retry_after
                        )
                    elif response.status >= 500:
                        if attempt < max_retries:
                            await asyncio.sleep(2**attempt)
                            self.stats["retries"] += 1
                            continue
                        raise ServiceUnavailableError("Service unavailable")

                    # Success
                    response_data = await response.json()
                    await self.rate_limiter.record_success(endpoint_path, method)
                    return response_data

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                    self.stats["retries"] += 1
                    continue

        self.stats["errors"] += 1
        raise RiotAPIError(f"Request failed: {str(last_error)}")

    def _extract_endpoint_path(self, url: str) -> str:
        """Extract endpoint path from URL for rate limiting."""
        stripped = url.replace("https://", "").replace("http://", "")
        parts = stripped.split("/", 1)
        if len(parts) == 2:
            return parts[1]
        return stripped

    # Account endpoints
    async def get_account_by_riot_id(
        self, game_name: str, tag_line: str, region: Optional[Region] = None
    ) -> AccountDTO:
        """Get account by Riot ID (gameName#tagLine)."""
        url = self.endpoints.account_by_riot_id(game_name, tag_line, region)
        response = await self._make_request(url)
        return AccountDTO(**response)

    # Summoner endpoints

    async def get_summoner_by_puuid(
        self, puuid: str, platform: Optional[Platform] = None
    ) -> SummonerDTO:
        """Get summoner by PUUID."""
        url = self.endpoints.summoner_by_puuid(puuid, platform)
        response = await self._make_request(url)
        return SummonerDTO(**response)

    # Match endpoints
    async def get_match_list_by_puuid(
        self,
        puuid: str,
        start: int = 0,
        count: int = 20,
        queue: Optional[Union[int, QueueType]] = None,
        type: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        region: Optional[Region] = None,
    ) -> MatchListDTO:
        """Get match list by PUUID."""
        # Normalize queue parameter to QueueType
        queue_type = self._normalize_queue_type(queue)

        url = self.endpoints.match_list_by_puuid(
            puuid, start, count, queue_type, type, start_time, end_time, region
        )
        response_data = await self._make_request(url)

        # Extract match IDs from response
        if isinstance(response_data, list):
            match_ids = response_data
        else:
            match_ids = response_data.get("matchIds", [])

        return MatchListDTO(match_ids=match_ids, start=start, count=count, puuid=puuid)

    async def get_match(
        self, match_id: str, region: Optional[Region] = None
    ) -> MatchDTO:
        """Get match details by match ID."""
        url = self.endpoints.match_by_id(match_id, region)
        response = await self._make_request(url)
        return MatchDTO(**response)

    # League endpoints
    async def get_league_entries_by_puuid(
        self, puuid: str, platform: Optional[Platform] = None
    ) -> List[LeagueEntryDTO]:
        """Get league entries by PUUID."""
        url = self.endpoints.league_entries_by_puuid(puuid, platform)
        response = await self._make_request(url)

        # API returns a list of league entries
        if not isinstance(response, list):
            raise RiotAPIError(
                f"Expected list response for league entries, got {type(response)}"
            )

        return [LeagueEntryDTO(**entry) for entry in response]

    # Utility methods

    @staticmethod
    def _normalize_queue_type(
        queue: Optional[Union[int, str, QueueType]],
    ) -> Optional[QueueType]:
        """
        Normalize queue parameter to QueueType enum.

        Args:
            queue: Queue ID as int, string, QueueType enum, or None

        Returns:
            QueueType enum or None

        Notes:
            - If queue is already QueueType, return as-is
            - If queue is int or str, try to find matching QueueType
            - If no match found, return None (let Riot API handle invalid values)
        """
        if queue is None:
            return None

        if isinstance(queue, QueueType):
            return queue

        # Convert queue to int for comparison
        try:
            queue_int = int(queue) if isinstance(queue, str) else queue
        except (ValueError, TypeError):
            logger.warning("Invalid queue type", queue=queue)
            return None

        # Try to find matching QueueType by value
        for queue_type in QueueType:
            if queue_type.value == queue_int:
                return queue_type

        # If no exact match, return None
        # Alternative: Could pass raw int and let Riot API validate
        logger.warning("Unknown queue type", queue=queue)
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        rate_limiter_stats = self.rate_limiter.get_stats()

        return {
            "client": self.stats.copy(),
            "rate_limiter": rate_limiter_stats,
            "region": self.region.value,
            "platform": self.platform.value,
        }
