"""Riot API HTTP client with proper rate limiting, error handling, and authentication."""

import asyncio
from typing import Optional, Dict, Any, List, Union
import aiohttp
import structlog

from ..config import get_global_settings
from .rate_limiter import RateLimiter
from .errors import RiotAPIError
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

        # Initialize components
        self.rate_limiter = RateLimiter()
        self.endpoints = RiotAPIEndpoints(self.region, self.platform)

        # HTTP session
        self.session = None
        self._session_lock = asyncio.Lock()

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

                    logger.info(
                        "Riot API client session started",
                        region=self._enum_str(self.region),
                        platform=self._enum_str(self.platform),
                        api_key_prefix="[REDACTED]" if self.api_key else "None",
                    )

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("Riot API client session closed")

    def _raise_client_error_if_needed(self, status: int) -> None:
        """Raise RiotAPIError for non-retryable client errors."""
        error_messages = {
            400: "Invalid request parameters",
            401: "Invalid API key",
            403: "Access forbidden",
            404: "Resource not found",
        }
        if status in error_messages:
            raise RiotAPIError(error_messages[status], status_code=status)

    def _handle_rate_limit(
        self, headers: dict, attempt: int, max_retries: int
    ) -> tuple[bool, int]:
        """Handle rate limit (429) with retry logic."""
        retry_after = int(headers.get("Retry-After", 1))
        if attempt < max_retries:
            return (True, retry_after)
        raise RiotAPIError(
            "Rate limit exceeded",
            status_code=429,
            retry_after=retry_after,
            app_rate_limit=headers.get("X-App-Rate-Limit"),
            method_rate_limit=headers.get("X-Method-Rate-Limit"),
        )

    def _handle_server_error(
        self, status: int, attempt: int, max_retries: int
    ) -> tuple[bool, int]:
        """Handle server errors (5xx) with exponential backoff."""
        if attempt < max_retries:
            return (True, 2**attempt)
        raise RiotAPIError("Service unavailable", status_code=status)

    async def _handle_http_error_status(
        self, status: int, headers: dict, attempt: int, max_retries: int
    ) -> tuple[bool, int]:
        """
        Handle HTTP error status codes.

        Returns:
            Tuple of (should_retry, sleep_seconds)

        Raises:
            RiotAPIError: For non-retryable errors
        """
        # Non-retryable client errors
        self._raise_client_error_if_needed(status)

        # Rate limit - retryable
        if status == 429:
            return self._handle_rate_limit(headers, attempt, max_retries)

        # Server errors - retryable with exponential backoff
        if status >= 500:
            return self._handle_server_error(status, attempt, max_retries)

        return (False, 0)

    async def _execute_single_request(
        self,
        url: str,
        method: str,
        params: Optional[Dict[str, Any]],
        data: Optional[Dict[str, Any]],
        endpoint_path: str,
        attempt: int,
        max_retries: int,
    ) -> Any:
        """Execute a single HTTP request with error handling."""
        if self.session is None:
            raise RiotAPIError("Session not initialized")

        async with self.session.request(
            method, url, params=params, json=data
        ) as response:
            self.rate_limiter.update_limits(
                dict(response.headers), endpoint_path, method
            )

            # Handle error status codes
            if response.status != 200:
                should_retry, sleep_seconds = await self._handle_http_error_status(
                    response.status, dict(response.headers), attempt, max_retries
                )
                if should_retry:
                    await asyncio.sleep(sleep_seconds)
                    return None  # Signal to retry

            # Success
            response_data = await response.json()
            await self.rate_limiter.record_success(endpoint_path, method)
            return response_data

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

        # Retry loop
        max_retries = 3 if retry_on_failure else 0
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                result = await self._execute_single_request(
                    url, method, params, data, endpoint_path, attempt, max_retries
                )
                if result is not None:
                    return result
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)

        raise RiotAPIError(f"Request failed: {str(last_error)}")

    def _extract_endpoint_path(self, url: str) -> str:
        """Extract endpoint path from URL for rate limiting."""
        stripped = url.replace("https://", "").replace("http://", "")
        parts = stripped.split("/", 1)
        if len(parts) == 2:
            return parts[1]
        return stripped

    @staticmethod
    def _enum_str(value: Union[Region, Platform, str]) -> str:
        """Extract string value from enum or return as-is."""
        return value.value if hasattr(value, "value") else value

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
        """Normalize queue parameter to QueueType enum."""
        if queue is None or isinstance(queue, QueueType):
            return queue

        try:
            queue_int = int(queue) if isinstance(queue, str) else queue
            for queue_type in QueueType:
                if queue_type.value == queue_int:
                    return queue_type
        except (ValueError, TypeError):
            pass

        return None
