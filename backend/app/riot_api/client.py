"""Riot API HTTP client with proper rate limiting, error handling, and authentication."""

import asyncio
import json
from typing import Optional, Dict, Any, List, Union
import aiohttp
import structlog

from ..config import settings
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
    CurrentGameInfoDTO,
    FeaturedGamesDTO,
    ActiveShardDTO,
)
from .cache import RiotAPICache
from .endpoints import RiotAPIEndpoints, Region, Platform, QueueType

logger = structlog.get_logger(__name__)


class RiotAPIClient:
    """Comprehensive Riot API client with rate limiting, caching, and error handling."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        region: Optional[Region] = None,
        platform: Optional[Platform] = None,
        enable_cache: bool = True,
        cache_size: int = 1000,
        enable_logging: bool = True,
    ):
        """
        Initialize Riot API client.

        Args:
            api_key: Riot API key (uses config if None)
            region: Default region for regional endpoints
            platform: Default platform for platform endpoints
            enable_cache: Enable response caching
            cache_size: Maximum cache size
            enable_logging: Enable request/response logging
        """
        self.api_key = api_key or settings.riot_api_key
        self.region = region or Region(settings.riot_region.lower())
        self.platform = platform or Platform(settings.riot_platform.lower())
        self.enable_cache = enable_cache
        self.enable_logging = enable_logging

        # Initialize components
        self.rate_limiter = RateLimiter()
        self.endpoints = RiotAPIEndpoints(self.region, self.platform)
        self.cache = RiotAPICache if enable_cache else None

        # HTTP session
        self.session = None
        self._session_lock = asyncio.Lock()

        # Statistics
        self.stats = {
            "requests_made": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "retries": 0,
            "errors": 0,
        }

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
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
                        region=self.region.value,
                        platform=self.platform.value,
                        api_key_prefix=self.api_key[:10] + "..."
                        if self.api_key
                        else "None",
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
        use_cache: bool = True,
        retry_on_failure: bool = True,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with rate limiting, caching, and retry logic.

        Args:
            url: Request URL
            method: HTTP method
            params: Query parameters
            data: Request body data
            use_cache: Use caching for this request
            retry_on_failure: Retry on transient failures

        Returns:
            Response data as dictionary

        Raises:
            RiotAPIError: For API errors
        """
        await self.start_session()

        # Cache checking is done at the method level (get_account_by_riot_id, get_match, etc.)
        # Generic request caching removed to use endpoint-specific caching

        # Rate limiting
        endpoint_path = self._extract_endpoint_path(url)
        await self.rate_limiter.wait_if_needed(endpoint_path, method)

        # Request with retry logic
        max_retries = 3 if retry_on_failure else 0
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                self.stats["requests_made"] += 1

                if self.enable_logging:
                    logger.info(
                        "Making API request",
                        url=url,
                        method=method,
                        attempt=attempt + 1,
                        max_retries=max_retries + 1,
                    )

                async with self.session.request(
                    method, url, params=params, json=data
                ) as response:
                    # Track rate limits from headers
                    self.rate_limiter.update_limits(
                        dict(response.headers), endpoint_path, method
                    )

                    # Handle response
                    if response.status == 400:
                        raise BadRequestError("Invalid request parameters")

                    elif response.status == 401:
                        raise AuthenticationError("Invalid API key")

                    elif response.status == 403:
                        raise ForbiddenError(
                            "Access forbidden - may be deprecated endpoint or insufficient API key permissions"
                        )

                    elif response.status == 404:
                        raise NotFoundError("Resource not found")

                    elif response.status == 429:
                        # Extract Retry-After header first, fallback to rate_limiter calculation
                        retry_after_header = response.headers.get("Retry-After")
                        if retry_after_header:
                            retry_after = int(retry_after_header)
                        else:
                            retry_after = await self.rate_limiter.handle_429(
                                dict(response.headers), endpoint_path
                            )

                        if attempt < max_retries:
                            await asyncio.sleep(retry_after)
                            self.stats["retries"] += 1
                            continue
                        else:
                            raise RateLimitError(
                                "Rate limit exceeded and retries exhausted",
                                retry_after=retry_after,
                            )

                    elif response.status >= 500:
                        if attempt < max_retries:
                            backoff = await self.rate_limiter.calculate_backoff(attempt)
                            await asyncio.sleep(backoff)
                            self.stats["retries"] += 1
                            continue
                        else:
                            raise ServiceUnavailableError(
                                f"Service unavailable after {max_retries} retries"
                            )

                    # Success response
                    response_data = await response.json()

                    # Caching is done at the method level (get_account_by_riot_id, get_match, etc.)

                    # Record success
                    await self.rate_limiter.record_success(endpoint_path, method)

                    if self.enable_logging:
                        logger.debug(
                            "API request successful",
                            url=url,
                            status=response.status,
                            response_size=len(str(response_data)),
                        )

                    return response_data

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                await self.rate_limiter.record_failure(
                    endpoint_path, method, error_type="timeout"
                )

                if attempt < max_retries:
                    backoff = await self.rate_limiter.calculate_backoff(attempt)
                    await asyncio.sleep(backoff)
                    self.stats["retries"] += 1
                    continue
                else:
                    break

        # All retries failed
        self.stats["errors"] += 1
        raise RiotAPIError(
            f"Request failed after {max_retries} retries: {str(last_error)}"
        )

    def _generate_cache_key(
        self,
        url: str,
        method: str,
        params: Optional[Dict[str, Any]],
        data: Optional[Dict[str, Any]],
    ) -> str:
        """Generate cache key for request."""
        key_parts = [method, url]
        if params:
            sorted_params = sorted(params.items())
            key_parts.append(json.dumps(sorted_params, sort_keys=True))
        if data:
            key_parts.append(json.dumps(data, sort_keys=True))
        return "|".join(key_parts)

    def _extract_endpoint_path(self, url: str) -> str:
        """Extract endpoint path from URL for rate limiting."""
        # Remove base URL and extract the relevant path
        parts = url.replace("https://", "").replace("http://", "").split("/", 3)
        if len(parts) > 3:
            return parts[3]  # Return everything after the domain
        return url

    # Account endpoints
    async def get_account_by_riot_id(
        self, game_name: str, tag_line: str, region: Optional[Region] = None
    ) -> AccountDTO:
        """Get account by Riot ID (gameName#tagLine)."""
        if self.cache:
            cached = self.cache.get_account_by_riot_id(game_name, tag_line)
            if cached:
                return AccountDTO(**cached)

        url = self.endpoints.account_by_riot_id(game_name, tag_line, region)
        data = await self._make_request(url)

        if self.cache:
            self.cache.set_account_by_riot_id(game_name, tag_line, data)

        return AccountDTO(**data)

    async def get_account_by_puuid(
        self, puuid: str, region: Optional[Region] = None
    ) -> AccountDTO:
        """Get account by PUUID."""
        if self.cache:
            cached = self.cache.get_account_by_puuid(puuid)
            if cached:
                return AccountDTO(**cached)

        url = self.endpoints.account_by_puuid(puuid, region)
        data = await self._make_request(url)

        if self.cache:
            self.cache.set_account_by_puuid(puuid, data)

        return AccountDTO(**data)

    async def get_active_shard(
        self, puuid: str, game: str = "lol", region: Optional[Region] = None
    ) -> ActiveShardDTO:
        """Get active shard by PUUID."""
        if self.cache:
            cached = self.cache.get_active_shard(puuid, game)
            if cached:
                return ActiveShardDTO(**cached)

        url = self.endpoints.active_shard(puuid, game, region)
        data = await self._make_request(url)

        if self.cache:
            self.cache.set_active_shard(puuid, game, data)

        return ActiveShardDTO(**data)

    # Summoner endpoints
    async def get_summoner_by_name(
        self, summoner_name: str, platform: Optional[Platform] = None
    ) -> SummonerDTO:
        """Get summoner by name."""
        if self.cache:
            cached = self.cache.get_summoner_by_name(summoner_name)
            if cached:
                return SummonerDTO(**cached)

        url = self.endpoints.summoner_by_name(summoner_name, platform)
        data = await self._make_request(url)

        if self.cache:
            self.cache.set_summoner_by_name(summoner_name, data)

        return SummonerDTO(**data)

    async def get_summoner_by_puuid(
        self, puuid: str, platform: Optional[Platform] = None
    ) -> SummonerDTO:
        """Get summoner by PUUID."""
        if self.cache:
            cached = self.cache.get_summoner_by_puuid(puuid)
            if cached:
                return SummonerDTO(**cached)

        url = self.endpoints.summoner_by_puuid(puuid, platform)
        data = await self._make_request(url)

        if self.cache:
            self.cache.set_summoner_by_puuid(puuid, data)

        return SummonerDTO(**data)

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

        if self.cache:
            cached = self.cache.get_match_list(
                puuid,
                start,
                count,
                queue_type.value if queue_type else None,
                start_time,
                end_time,
            )
            if cached:
                return MatchListDTO(
                    match_ids=cached, start=start, count=count, puuid=puuid
                )

        url = self.endpoints.match_list_by_puuid(
            puuid, start, count, queue_type, type, start_time, end_time, region
        )
        data = await self._make_request(url)

        if self.cache:
            self.cache.set_match_list(
                puuid,
                start,
                count,
                data,
                queue_type.value if queue_type else None,
                start_time,
                end_time,
            )

        return MatchListDTO(match_ids=data, start=start, count=count, puuid=puuid)

    async def get_match(
        self, match_id: str, region: Optional[Region] = None
    ) -> MatchDTO:
        """Get match details by match ID."""
        if self.cache:
            cached = self.cache.get_match(match_id)
            if cached:
                return MatchDTO(**cached)

        url = self.endpoints.match_by_id(match_id, region)
        data = await self._make_request(url)

        if self.cache:
            self.cache.set_match(match_id, data)

        return MatchDTO(**data)

    async def get_match_timeline(
        self, match_id: str, region: Optional[Region] = None
    ) -> Dict[str, Any]:
        """Get match timeline by match ID."""
        url = self.endpoints.match_timeline_by_id(match_id, region)
        return await self._make_request(url)

    # League endpoints
    async def get_league_entries_by_summoner(
        self, summoner_id: str, platform: Optional[Platform] = None
    ) -> List[LeagueEntryDTO]:
        """Get league entries by summoner ID."""
        if self.cache:
            cached = self.cache.get_league_entries(summoner_id)
            if cached:
                return [LeagueEntryDTO(**entry) for entry in cached]

        url = self.endpoints.league_entries_by_summoner(summoner_id, platform)
        data = await self._make_request(url)

        if self.cache:
            self.cache.set_league_entries(summoner_id, data)

        return [LeagueEntryDTO(**entry) for entry in data]

    # Spectator endpoints
    async def get_active_game(
        self, summoner_id: str, platform: Optional[Platform] = None
    ) -> Optional[CurrentGameInfoDTO]:
        """Get active game by summoner ID."""
        if self.cache:
            cached = self.cache.get_active_game(summoner_id)
            if cached:
                return CurrentGameInfoDTO(**cached)

        url = self.endpoints.active_game_by_summoner(summoner_id, platform)

        try:
            data = await self._make_request(url)
            if self.cache:
                self.cache.set_active_game(summoner_id, data)
            return CurrentGameInfoDTO(**data)
        except NotFoundError:
            # No active game is normal, return None
            return None

    async def get_featured_games(
        self, platform: Optional[Platform] = None
    ) -> FeaturedGamesDTO:
        """Get featured games."""
        if self.cache:
            cached = self.cache.get_featured_games()
            if cached:
                return FeaturedGamesDTO(**cached)

        url = self.endpoints.featured_games(platform)
        data = await self._make_request(url)

        if self.cache:
            self.cache.set_featured_games(data)

        return FeaturedGamesDTO(**data)

    # Utility methods
    async def get_puuid_by_riot_id(
        self, game_name: str, tag_line: str, region: Optional[Region] = None
    ) -> str:
        """Get PUUID from Riot ID."""
        account = await self.get_account_by_riot_id(game_name, tag_line, region)
        return account.puuid

    async def get_puuid_by_summoner_name(
        self, summoner_name: str, platform: Optional[Platform] = None
    ) -> str:
        """Get PUUID from summoner name."""
        summoner = await self.get_summoner_by_name(summoner_name, platform)
        return summoner.puuid

    async def get_summoner_id_by_puuid(
        self, puuid: str, platform: Optional[Platform] = None
    ) -> str:
        """Get summoner ID from PUUID."""
        summoner = await self.get_summoner_by_puuid(puuid, platform)
        return summoner.id

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

        # Convert to string for comparison
        queue_str = str(queue)

        # Try to find matching QueueType by value
        for queue_type in QueueType:
            if queue_type.value == queue_str:
                return queue_type

        # If no exact match, return None
        # Alternative: Could pass raw int and let Riot API validate
        logger.warning("Unknown queue type", queue=queue)
        return None

    async def get_match_history_stats(
        self,
        puuid: str,
        queue: Union[int, QueueType] = QueueType.RANKED_SOLO,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        max_matches: int = 100,
    ) -> Dict[str, Any]:
        """
        Get match history statistics for a player.

        Args:
            puuid: Player PUUID
            queue: Queue type to filter (int or QueueType)
            start_time: Start time in epoch seconds
            end_time: End time in epoch seconds
            max_matches: Maximum number of matches to analyze

        Returns:
            Dictionary with statistics
        """
        # Normalize queue parameter
        queue_type = self._normalize_queue_type(queue)
        if queue_type is None:
            queue_type = QueueType.RANKED_SOLO

        # Get match list
        match_list = await self.get_match_list_by_puuid(
            puuid,
            start=0,
            count=max_matches,
            queue=queue_type,
            start_time=start_time,
            end_time=end_time,
        )

        # Get match details for each match
        matches = []
        wins = 0
        kills = 0
        deaths = 0
        assists = 0

        for match_id in match_list.match_ids[:max_matches]:
            try:
                match = await self.get_match(match_id)
                participant = match.get_participant_by_puuid(puuid)

                if participant:
                    matches.append(match)
                    if participant.win:
                        wins += 1
                    kills += participant.kills
                    deaths += participant.deaths
                    assists += participant.assists
            except Exception as e:
                logger.warning(
                    "Failed to get match for stats", match_id=match_id, error=str(e)
                )
                continue

        # Calculate statistics
        total_matches = len(matches)
        win_rate = (wins / total_matches * 100) if total_matches > 0 else 0
        avg_kills = kills / total_matches if total_matches > 0 else 0
        avg_deaths = deaths / total_matches if total_matches > 0 else 0
        avg_assists = assists / total_matches if total_matches > 0 else 0

        return {
            "puuid": puuid,
            "queue": queue_type.value,
            "total_matches": total_matches,
            "wins": wins,
            "losses": total_matches - wins,
            "win_rate": win_rate,
            "avg_kills": avg_kills,
            "avg_deaths": avg_deaths,
            "avg_assists": avg_assists,
            "kda": (kills + assists) / deaths if deaths > 0 else kills + assists,
            "start_time": start_time,
            "end_time": end_time,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        cache_stats = self.cache.get_stats() if self.cache else {}
        rate_limiter_stats = self.rate_limiter.get_stats()

        return {
            "client": self.stats.copy(),
            "cache": cache_stats,
            "rate_limiter": rate_limiter_stats,
            "region": self.region.value,
            "platform": self.platform.value,
            "cache_enabled": self.enable_cache,
        }

    async def clear_cache(self) -> None:
        """Clear all cached data."""
        if self.cache:
            self.cache.clear_all()
            logger.info("Client cache cleared")

    async def reset_rate_limiter(self) -> None:
        """Reset rate limiter state."""
        await self.rate_limiter.reset()
        logger.info("Rate limiter reset")
