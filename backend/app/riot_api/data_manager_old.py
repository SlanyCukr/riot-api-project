"""
RiotDataManager: Intelligent data management with database-first approach.

This module provides a unified interface for accessing Riot API data that:
1. Checks database first for existing data
2. Validates data freshness based on TTL policies
3. Respects rate limits and queues requests when needed
4. Provides graceful degradation with stale data fallbacks
5. Tracks usage patterns for optimization
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

from .client import RiotAPIClient
from .errors import RateLimitError
from .models import MatchDTO, LeagueEntryDTO
from .endpoints import Platform, Region
from ..models.data_tracking import DataTracking, APIRequestQueue, RateLimitLog
from ..models.players import Player
from ..models.matches import Match
from ..models.ranks import PlayerRank
from ..schemas.players import PlayerResponse

logger = logging.getLogger(__name__)


class FetchStatus(Enum):
    """Status of API fetch operations."""

    CAN_FETCH = "can_fetch"
    RATE_LIMITED = "rate_limited"
    CIRCUIT_OPEN = "circuit_open"


@dataclass
class FetchResult:
    """Result of a fetch operation."""

    can_fetch: bool
    reason: Optional[str] = None
    wait_time: Optional[float] = None
    priority_level: str = "normal"


@dataclass
class StaleDataWarning:
    """Wrapper for stale data with warning information."""

    data: Any
    stale_reason: str
    fresh_at: Optional[datetime] = None
    is_error_fallback: bool = False


class DataFreshnessManager:
    """Manages data freshness policies and TTL strategies."""

    # Freshness policies per data type
    FRESHNESS_POLICIES = {
        "account": timedelta(hours=24),  # Account data rarely changes
        "summoner": timedelta(hours=24),  # Summoner data rarely changes
        "match": timedelta(days=7),  # Match data is immutable
        "match_list": timedelta(minutes=5),  # Match lists change frequently
        "rank": timedelta(hours=1),  # Rank data changes regularly
        "active_game": timedelta(minutes=1),  # Live game data changes rapidly
        "featured_games": timedelta(minutes=2),  # Featured games change frequently
    }

    def __init__(self, db: AsyncSession):
        """Initialize freshness manager."""
        self.db = db

    def is_fresh(self, data_type: str, last_updated: datetime) -> bool:
        """Check if data is still fresh based on TTL policy."""
        policy = self.FRESHNESS_POLICIES.get(data_type, timedelta(hours=1))
        return datetime.now(timezone.utc) - last_updated < policy

    def get_freshness_policy(self, data_type: str) -> timedelta:
        """Get freshness policy for a data type."""
        return self.FRESHNESS_POLICIES.get(data_type, timedelta(hours=1))

    async def mark_data_fetched(self, data_type: str, identifier: str) -> None:
        """Mark data as freshly fetched in tracking table."""
        try:
            # Update existing record or create new one
            stmt = (
                update(DataTracking)
                .where(
                    and_(
                        DataTracking.data_type == data_type,
                        DataTracking.identifier == identifier,
                    )
                )
                .values(
                    last_fetched=datetime.now(timezone.utc),
                    last_updated=datetime.now(timezone.utc),
                    fetch_count=DataTracking.fetch_count + 1,
                    is_active=True,
                )
                .returning(DataTracking.id)
            )

            result = await self.db.execute(stmt)

            if not result.scalar_one_or_none():
                # Create new record if it doesn't exist
                new_tracking = DataTracking(
                    data_type=data_type,
                    identifier=identifier,
                    last_fetched=datetime.now(timezone.utc),
                    last_updated=datetime.now(timezone.utc),
                    fetch_count=1,
                    hit_count=0,
                )
                self.db.add(new_tracking)

            await self.db.commit()

        except Exception as e:
            logger.error(
                "Failed to mark data as fetched",
                extra={
                    "data_type": data_type,
                    "identifier": identifier,
                    "error": str(e),
                },
            )
            await self.db.rollback()

    async def mark_data_hit(self, data_type: str, identifier: str) -> None:
        """Mark data as accessed (hit) in tracking table."""
        try:
            stmt = (
                update(DataTracking)
                .where(
                    and_(
                        DataTracking.data_type == data_type,
                        DataTracking.identifier == identifier,
                    )
                )
                .values(
                    hit_count=DataTracking.hit_count + 1,
                    last_hit=datetime.now(timezone.utc),
                )
            )
            await self.db.execute(stmt)
            await self.db.commit()

        except Exception as e:
            logger.debug(
                "Failed to mark data hit (tracking record may not exist)",
                extra={
                    "data_type": data_type,
                    "identifier": identifier,
                    "error": str(e),
                },
            )

    async def get_freshness_status(
        self, data_type: str, identifier: str
    ) -> Optional[DataTracking]:
        """Get freshness status for data."""
        try:
            stmt = select(DataTracking).where(
                and_(
                    DataTracking.data_type == data_type,
                    DataTracking.identifier == identifier,
                    DataTracking.is_active,
                )
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                "Failed to get freshness status",
                extra={
                    "data_type": data_type,
                    "identifier": identifier,
                    "error": str(e),
                },
            )
            return None


class RateLimitAwareFetcher:
    """Intelligent fetcher that respects rate limits and manages queues."""

    def __init__(self, api_client: RiotAPIClient, db: AsyncSession):
        """Initialize rate limit aware fetcher."""
        self.api_client = api_client
        self.db = db
        self.rate_limiter = api_client.rate_limiter

    async def can_fetch(self, priority: str = "normal") -> FetchResult:
        """Check if we can make API calls based on rate limits."""
        try:
            # Get current rate limit status
            stats = self.rate_limiter.get_stats()

            # Check app-level limits
            app_usage = 0
            app_limit = 20  # Default rate limit
            for limit_name, limit_stats in stats.get("app_limits", {}).items():
                current_usage = limit_stats.get("current_usage", 0)
                max_requests = limit_stats.get("max_requests", 20)
                app_usage = max(app_usage, current_usage / max_requests)
                app_limit = max(app_limit, max_requests)

            # Use buffer zones to be conservative
            app_buffer = 0.8  # Don't exceed 80% of limits

            if app_usage > app_buffer:
                wait_time = 60.0  # Conservative wait time
                return FetchResult(
                    can_fetch=False,
                    reason=f"Near app rate limit ({app_usage:.1%} usage)",
                    wait_time=wait_time,
                    priority_level="low",
                )

            # Check circuit breakers
            for circuit_name, breaker_stats in stats.get(
                "circuit_breakers", {}
            ).items():
                if breaker_stats.get("state") == "open":
                    return FetchResult(
                        can_fetch=False,
                        reason=f"Circuit breaker '{circuit_name}' is open",
                        wait_time=breaker_stats.get("time_since_failure", 30.0),
                        priority_level="low",
                    )

            return FetchResult(can_fetch=True, priority_level=priority)

        except Exception:
            logger.error("Failed to check rate limit status", exc_info=True)
            # Be conservative and assume we can't fetch
            return FetchResult(
                can_fetch=False,
                reason="Unable to check rate limit status",
                wait_time=5.0,
                priority_level="low",
            )

    async def log_rate_limit_event(
        self, limit_type: str, endpoint: str, retry_after: Optional[int] = None
    ) -> None:
        """Log rate limit events for analysis."""
        try:
            log_entry = RateLimitLog(
                limit_type=limit_type,
                endpoint=endpoint,
                retry_after=retry_after,
                created_at=datetime.now(timezone.utc),
            )
            self.db.add(log_entry)
            await self.db.commit()

        except Exception:
            logger.error("Failed to log rate limit event", exc_info=True)
            await self.db.rollback()

    async def queue_request(
        self,
        data_type: str,
        identifier: str,
        priority: str = "normal",
        scheduled_at: Optional[datetime] = None,
        request_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Queue a request for background processing."""
        try:
            if scheduled_at is None:
                # Default to 5 minutes from now for normal priority
                if priority == "urgent":
                    scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=30)
                elif priority == "high":
                    scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=2)
                elif priority == "low":
                    scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=15)
                else:  # normal
                    scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=5)

            queued_request = APIRequestQueue(
                data_type=data_type,
                identifier=identifier,
                priority=priority,
                scheduled_at=scheduled_at,
                status="pending",
                request_data=json.dumps(request_data) if request_data else None,
            )

            self.db.add(queued_request)
            await self.db.commit()

            logger.info(
                "Queued API request",
                extra={
                    "data_type": data_type,
                    "identifier": identifier,
                    "priority": priority,
                    "scheduled_at": str(scheduled_at),
                },
            )

        except Exception as e:
            logger.error(
                "Failed to queue request",
                extra={
                    "data_type": data_type,
                    "identifier": identifier,
                    "error": str(e),
                },
            )
            await self.db.rollback()


class SmartFetchStrategy:
    """Determines optimal fetching strategy based on data type and usage patterns."""

    def __init__(self, db: AsyncSession, api_client: RiotAPIClient):
        """Initialize smart fetch strategy."""
        self.db = db
        self.api_client = api_client
        self.freshness_manager = DataFreshnessManager(db)
        self.rate_limit_fetcher = RateLimitAwareFetcher(api_client, db)

    async def get_data(
        self,
        data_type: str,
        identifier: str,
        force_refresh: bool = False,
        priority: str = "normal",
        **kwargs: Any,
    ) -> Union[Any, StaleDataWarning]:
        """
        Retrieve data using intelligent caching and rate limit management.

        Args:
            data_type: Type of data to fetch (account, summoner, match, etc.)
            identifier: Unique identifier for the data
            force_refresh: Force refresh even if data is fresh
            priority: Priority level for the request
            **kwargs: Additional parameters for the fetch operation

        Returns:
            Fresh data, stale data with warning, or raises exception
        """
        try:
            # 1. Check database first
            cached_data = await self._get_from_database(data_type, identifier)

            # 2. Check if data is fresh (unless force refresh)
            if cached_data and not force_refresh:
                freshness_status = await self.freshness_manager.get_freshness_status(
                    data_type, identifier
                )

                if freshness_status and self.freshness_manager.is_fresh(
                    data_type, freshness_status.last_fetched
                ):
                    await self.freshness_manager.mark_data_hit(data_type, identifier)
                    logger.debug(
                        "Data served from database (fresh)",
                        extra={
                            "data_type": data_type,
                            "identifier": identifier,
                            "age_hours": freshness_status.age_hours,
                        },
                    )
                    return cached_data

            # 3. Check if we can make API calls
            fetch_status = await self.rate_limit_fetcher.can_fetch(priority)

            if not fetch_status.can_fetch:
                # Return stale data with warning if available
                if cached_data:
                    await self.freshness_manager.mark_data_hit(data_type, identifier)
                    logger.warning(
                        "Serving stale data due to rate limits",
                        extra={
                            "data_type": data_type,
                            "identifier": identifier,
                            "reason": fetch_status.reason,
                            "wait_time": fetch_status.wait_time,
                        },
                    )

                    return StaleDataWarning(
                        data=cached_data,
                        stale_reason=fetch_status.reason or "Data is stale",
                        fresh_at=datetime.now(timezone.utc)
                        + timedelta(seconds=fetch_status.wait_time or 60),
                    )

                # Queue the request if no cached data available
                if priority in ["urgent", "high"]:
                    await self.rate_limit_fetcher.queue_request(
                        data_type,
                        identifier,
                        priority,
                        scheduled_at=None,
                        request_data=kwargs,
                    )

                raise RateLimitError(
                    f"Rate limit active: {fetch_status.reason}",
                    retry_after=fetch_status.wait_time,
                )

            # 4. Fetch fresh data from API
            try:
                fresh_data = await self._fetch_from_api(data_type, identifier, **kwargs)

                # Store in database
                await self._store_in_database(data_type, identifier, fresh_data)

                # Mark as freshly fetched
                await self.freshness_manager.mark_data_fetched(data_type, identifier)

                logger.info(
                    "Data fetched from API and stored",
                    extra={
                        "data_type": data_type,
                        "identifier": identifier,
                    },
                )

                return fresh_data

            except Exception as e:
                logger.error(
                    "Failed to fetch from API",
                    extra={
                        "data_type": data_type,
                        "identifier": identifier,
                        "error": str(e),
                    },
                )

                # Fallback to stale data if API fails
                if cached_data:
                    await self.freshness_manager.mark_data_hit(data_type, identifier)
                    return StaleDataWarning(
                        data=cached_data,
                        stale_reason=f"API error: {str(e)}",
                        is_error_fallback=True,
                    )

                # Queue for retry if API fails completely
                await self.rate_limit_fetcher.queue_request(
                    data_type,
                    identifier,
                    priority,
                    scheduled_at=None,
                    request_data=kwargs,
                )

                raise

        except Exception as e:
            logger.error(
                "Smart fetch failed",
                extra={
                    "data_type": data_type,
                    "identifier": identifier,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def _get_from_database(
        self, data_type: str, identifier: str
    ) -> Optional[Any]:
        """Get data from database based on type."""
        try:
            if data_type == "player":
                # Handle both riot_id and puuid identifiers
                if "#" in identifier:  # riot_id format
                    stmt = select(Player).where(Player.riot_id == identifier)
                else:  # puuid format
                    stmt = select(Player).where(Player.puuid == identifier)

                result = await self.db.execute(stmt)
                player = result.scalar_one_or_none()
                return PlayerResponse.model_validate(player) if player else None

            elif data_type == "match":
                stmt = select(Match).where(Match.match_id == identifier)
                result = await self.db.execute(stmt)
                return result.scalar_one_or_none()

            elif data_type == "rank":
                stmt = (
                    select(PlayerRank)
                    .where(
                        and_(
                            PlayerRank.puuid == identifier,
                            PlayerRank.is_current,
                        )
                    )
                    .order_by(PlayerRank.updated_at.desc())
                )
                result = await self.db.execute(stmt)
                return result.scalar_one_or_none()

            # Add more data types as needed
            else:
                logger.warning(
                    "Unknown data type for database lookup",
                    extra={"data_type": data_type},
                )
                return None

        except Exception as e:
            logger.error(
                "Failed to get data from database",
                extra={
                    "data_type": data_type,
                    "identifier": identifier,
                    "error": str(e),
                },
            )
            return None

    async def _fetch_from_api(
        self, data_type: str, identifier: str, **kwargs: Any
    ) -> Any:
        """Fetch data from Riot API based on type."""
        if data_type == "player":
            if "#" in identifier:  # riot_id format
                game_name, tag_line = identifier.split("#", 1)
                platform_str: str = str(kwargs.get("platform", "eun1"))
                platform = Platform(platform_str)
                account = await self.api_client.get_account_by_riot_id(
                    game_name, tag_line
                )
                summoner = await self.api_client.get_summoner_by_puuid(
                    account.puuid, platform
                )

                # Convert to player response format
                return {
                    "puuid": account.puuid,
                    "riot_id": game_name,
                    "tag_line": tag_line,
                    "summoner_name": game_name,  # Use game_name as API doesn't return name
                    "platform": platform,
                    "account_level": summoner.summoner_level,
                    "profile_icon_id": summoner.profile_icon_id,
                    "summoner_id": summoner.id,
                }
            else:  # puuid format
                platform_str: str = str(kwargs.get("platform", "eun1"))
                platform = Platform(platform_str)
                summoner = await self.api_client.get_summoner_by_puuid(
                    identifier, platform
                )
                return {
                    "puuid": identifier,
                    "summoner_name": summoner.name,
                    "platform": platform,
                    "account_level": summoner.summoner_level,
                    "profile_icon_id": summoner.profile_icon_id,
                    "summoner_id": summoner.id,
                }

        elif data_type == "match":
            region_str: str = str(kwargs.get("region", "europe"))
            region = Region(region_str)
            return await self.api_client.get_match(identifier, region)

        elif data_type == "rank":
            platform_str: str = str(kwargs.get("platform", "eun1"))
            platform = Platform(platform_str)
            # Need summoner_id for league entries
            summoner = await self.api_client.get_summoner_by_puuid(identifier, platform)
            if summoner.id is None:
                raise ValueError(f"Summoner ID is None for PUUID: {identifier}")
            return await self.api_client.get_league_entries_by_summoner(
                summoner.id, platform
            )

        else:
            raise ValueError(f"Unknown data type: {data_type}")

    async def _store_in_database(
        self, data_type: str, identifier: str, data: Any
    ) -> None:
        """Store data in database based on type."""
        try:
            if data_type == "player":
                # Check if player exists
                stmt = select(Player).where(Player.puuid == data["puuid"])
                result = await self.db.execute(stmt)
                player = result.scalar_one_or_none()

                if player:
                    # Update existing player
                    for key, value in data.items():
                        if hasattr(player, key):
                            setattr(player, key, value)
                    player.updated_at = datetime.now(timezone.utc)
                    player.last_seen = datetime.now(timezone.utc)
                else:
                    # Create new player
                    player = Player(
                        puuid=data["puuid"],
                        riot_id=data.get("riot_id"),
                        tag_line=data.get("tag_line"),
                        summoner_name=data.get("summoner_name"),
                        platform=data.get("platform"),
                        account_level=data.get("account_level"),
                        profile_icon_id=data.get("profile_icon_id"),
                        summoner_id=data.get("summoner_id"),
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                        last_seen=datetime.now(timezone.utc),
                    )
                    self.db.add(player)

            elif data_type == "match":
                # Store match data (implementation would depend on match model structure)
                pass  # Implementation depends on exact match model structure

            elif data_type == "rank":
                # Store rank data (implementation would depend on rank model structure)
                pass  # Implementation depends on exact rank model structure

            await self.db.commit()

        except Exception as e:
            logger.error(
                "Failed to store data in database",
                extra={
                    "data_type": data_type,
                    "identifier": identifier,
                    "error": str(e),
                },
            )
            await self.db.rollback()


class RiotDataManager:
    """
    Main interface for all Riot API data operations.

    This class provides a unified interface that intelligently manages
    data flow between database, Riot API, and user requests.
    """

    def __init__(self, db: AsyncSession, api_client: RiotAPIClient):
        """Initialize Riot data manager."""
        self.db = db
        self.api_client = api_client
        self.smart_fetcher = SmartFetchStrategy(db, api_client)
        self.freshness_manager = DataFreshnessManager(db)
        self.rate_limit_fetcher = RateLimitAwareFetcher(api_client, db)

    # Player Data Methods
    async def get_player_by_riot_id(
        self, game_name: str, tag_line: str, platform: str
    ) -> PlayerResponse:
        """Get player data with intelligent fetching."""
        try:
            # Convert platform string to Platform enum
            platform_enum = Platform(platform.lower())

            result = await self.smart_fetcher.get_data(
                "player",
                f"{game_name}#{tag_line}",
                platform=platform_enum,
            )

            # Handle stale data warnings
            if isinstance(result, StaleDataWarning):
                logger.warning(
                    "Returning stale player data",
                    extra={
                        "game_name": game_name,
                        "tag_line": tag_line,
                        "reason": result.stale_reason,
                    },
                )
                return result.data

            return result

        except Exception as e:
            logger.error(
                "Failed to get player by riot ID",
                extra={
                    "game_name": game_name,
                    "tag_line": tag_line,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def get_player_by_puuid(
        self, puuid: str, platform: str = "eun1"
    ) -> PlayerResponse:
        """Get player by PUUID with intelligent fetching."""
        try:
            result = await self.smart_fetcher.get_data(
                "player",
                puuid,
                platform=platform,
            )

            # Handle stale data warnings
            if isinstance(result, StaleDataWarning):
                logger.warning(
                    "Returning stale player data",
                    extra={
                        "puuid": puuid,
                        "reason": result.stale_reason,
                    },
                )
                return result.data

            return result

        except Exception as e:
            logger.error(
                "Failed to get player by PUUID",
                extra={
                    "puuid": puuid,
                    "error": str(e),
                },
            )
            raise

    # Match Data Methods
    async def get_match(self, match_id: str, region: str = "europe") -> MatchDTO:
        """Get match data (immutable, stored permanently)."""
        try:
            result = await self.smart_fetcher.get_data(
                "match",
                match_id,
                region=region,
            )

            if isinstance(result, StaleDataWarning):
                # Match data shouldn't be stale since it's immutable, but handle gracefully
                return result.data

            return result

        except Exception as e:
            logger.error(
                "Failed to get match",
                extra={
                    "match_id": match_id,
                    "error": str(e),
                },
            )
            raise

    # Rank Data Methods
    async def get_player_ranks(
        self, puuid: str, platform: str = "eun1"
    ) -> List[LeagueEntryDTO]:
        """Get player rank data with 1-hour freshness."""
        try:
            result = await self.smart_fetcher.get_data(
                "rank",
                puuid,
                platform=platform,
            )

            if isinstance(result, StaleDataWarning):
                logger.warning(
                    "Returning stale rank data",
                    extra={
                        "puuid": puuid,
                        "reason": result.stale_reason,
                    },
                )
                return result.data

            return result

        except Exception as e:
            logger.error(
                "Failed to get player ranks",
                extra={
                    "puuid": puuid,
                    "error": str(e),
                },
            )
            raise

    # Real-time Data Methods (no caching)
    async def get_active_game(
        self, summoner_id: str, platform: str = "eun1"
    ) -> Optional[Any]:
        """Get active game (always fresh, no caching)."""
        try:
            # Convert platform string to Platform enum
            platform_enum = Platform(platform.lower())
            # For real-time data, always call API directly
            return await self.api_client.get_active_game(summoner_id, platform_enum)

        except Exception as e:
            logger.error(
                "Failed to get active game",
                extra={
                    "summoner_id": summoner_id,
                    "error": str(e),
                },
            )
            return None

    # Utility Methods
    async def refresh_player_data(
        self, puuid: str, platform: str = "eun1"
    ) -> PlayerResponse:
        """Force refresh player data from API."""
        try:
            result = await self.smart_fetcher.get_data(
                "player",
                puuid,
                platform=platform,
                force_refresh=True,
                priority="high",
            )

            if isinstance(result, StaleDataWarning):
                # Even with force refresh, we might get stale data due to rate limits
                logger.warning(
                    "Force refresh returned stale data",
                    extra={
                        "puuid": puuid,
                        "reason": result.stale_reason,
                    },
                )
                return result.data

            return result

        except Exception as e:
            logger.error(
                "Failed to refresh player data",
                extra={
                    "puuid": puuid,
                    "error": str(e),
                },
            )
            raise

    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status for UI."""
        try:
            fetch_status = await self.rate_limit_fetcher.can_fetch()
            stats = self.api_client.get_stats()

            return {
                "can_fetch": fetch_status.can_fetch,
                "reason": fetch_status.reason,
                "wait_time": fetch_status.wait_time,
                "priority_level": fetch_status.priority_level,
                "api_stats": stats,
                "circuit_breakers": stats.get("rate_limiter", {}).get(
                    "circuit_breakers", {}
                ),
            }

        except Exception:
            logger.error("Failed to get rate limit status", exc_info=True)
            return {
                "can_fetch": False,
                "reason": "Unable to get status",
                "wait_time": 60.0,
                "priority_level": "low",
            }

    async def queue_background_refresh(
        self, data_type: str, identifier: str, priority: str = "normal"
    ) -> None:
        """Queue background data refresh."""
        await self.rate_limit_fetcher.queue_request(data_type, identifier, priority)

    async def get_data_stats(self) -> Dict[str, Any]:
        """Get comprehensive data management statistics."""
        try:
            # Get tracking stats
            tracking_stats = {}
            for data_type in self.freshness_manager.FRESHNESS_POLICIES.keys():
                stmt = select(DataTracking).where(DataTracking.data_type == data_type)
                result = await self.db.execute(stmt)
                records = result.scalars().all()

                if records:
                    total_records = len(records)
                    total_hits = sum(r.hit_count for r in records)
                    total_fetches = sum(r.fetch_count for r in records)
                    avg_age = sum(r.age_hours for r in records) / total_records

                    tracking_stats[data_type] = {
                        "total_records": total_records,
                        "total_hits": total_hits,
                        "total_fetches": total_fetches,
                        "hit_rate": (
                            total_hits / total_fetches if total_fetches > 0 else 0
                        ),
                        "avg_age_hours": avg_age,
                    }
                else:
                    tracking_stats[data_type] = {
                        "total_records": 0,
                        "total_hits": 0,
                        "total_fetches": 0,
                        "hit_rate": 0,
                        "avg_age_hours": 0,
                    }

            # Get queue stats
            queue_stmt = select(APIRequestQueue).where(
                APIRequestQueue.status == "pending"
            )
            queue_result = await self.db.execute(queue_stmt)
            pending_requests = len(queue_result.scalars().all())

            # Get rate limit stats
            rate_limit_stmt = select(RateLimitLog).where(
                RateLimitLog.created_at
                > datetime.now(timezone.utc) - timedelta(hours=24)
            )
            rate_limit_result = await self.db.execute(rate_limit_stmt)
            recent_rate_limits = len(rate_limit_result.scalars().all())

            return {
                "tracking_stats": tracking_stats,
                "pending_requests": pending_requests,
                "recent_rate_limits": recent_rate_limits,
                "rate_limit_status": await self.get_rate_limit_status(),
            }

        except Exception as e:
            logger.error("Failed to get data stats", exc_info=True)
            return {"error": str(e)}
