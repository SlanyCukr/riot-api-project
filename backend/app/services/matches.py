"""Match service for handling match data operations."""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from ..models.matches import Match
from ..models.participants import MatchParticipant
from ..models.players import Player
from ..schemas.matches import (
    MatchResponse,
    MatchListResponse,
    MatchStatsResponse,
)
from ..riot_api.transformers import MatchTransformer
from ..riot_api.errors import RiotAPIError
from ..utils.statistics import safe_divide

if TYPE_CHECKING:
    from ..riot_api.client import RiotAPIClient

logger = structlog.get_logger(__name__)


class MatchService:
    """Service for handling match data operations."""

    def __init__(self, db: AsyncSession):
        """Initialize match service with database session only."""
        self.db = db
        self.transformer = MatchTransformer()

    async def get_player_matches(
        self,
        puuid: str,
        start: int = 0,
        count: int = 20,
        queue: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> MatchListResponse:
        """
        Get match history for a player from database only.

        Never calls Riot API - returns whatever matches are available in database.
        Supports pagination for infinite scroll.

        Args:
            puuid: Player PUUID
            start: Start index for pagination
            count: Number of matches to return
            queue: Filter by queue ID
            start_time: Start timestamp
            end_time: End timestamp

        Returns:
            MatchListResponse with matches from database
        """
        try:
            # Get matches from database only
            db_matches = await self._get_matches_from_db(
                puuid, start, count, queue, start_time, end_time
            )

            # Get total count of matches for pagination
            total_count = await self._count_matches_from_db(
                puuid, queue, start_time, end_time
            )

            match_responses = [
                MatchResponse.model_validate(match) for match in db_matches
            ]

            # Calculate page-based pagination from start/count
            page = (start // count) if count > 0 else 0
            size = count
            pages = ((total_count + count - 1) // count) if count > 0 else 0

            logger.debug(
                "Retrieved matches from database",
                puuid=puuid,
                matches_count=len(match_responses),
                total_count=total_count,
                page=page,
                size=size,
            )

            return MatchListResponse(
                matches=match_responses,
                total=total_count,
                page=page,
                size=size,
                pages=pages,
            )
        except Exception as e:
            logger.error(
                "Failed to get player matches from database", puuid=puuid, error=str(e)
            )
            raise

    @staticmethod
    def _create_empty_stats_response(puuid: str) -> MatchStatsResponse:
        """Create stats response for players with no matches."""
        return MatchStatsResponse(
            puuid=puuid,
            total_matches=0,
            wins=0,
            losses=0,
            win_rate=0.0,
            avg_kills=0.0,
            avg_deaths=0.0,
            avg_assists=0.0,
            avg_kda=0.0,
            avg_cs=0.0,
            avg_vision_score=0.0,
        )

    @staticmethod
    def _aggregate_participant_stats(
        matches: list, participants_by_match: dict
    ) -> tuple[int, int, int, int, int, int]:
        """
        Aggregate statistics from match participants.

        Returns:
            Tuple of (kills, deaths, assists, cs, vision, wins)
        """
        totals = {
            "kills": 0,
            "deaths": 0,
            "assists": 0,
            "cs": 0,
            "vision": 0,
            "wins": 0,
        }

        for match in matches:
            participant = participants_by_match.get(match.match_id)
            if participant:
                totals["kills"] += participant.kills
                totals["deaths"] += participant.deaths
                totals["assists"] += participant.assists
                totals["cs"] += participant.cs
                totals["vision"] += participant.vision_score
                if participant.win:
                    totals["wins"] += 1

        return (
            totals["kills"],
            totals["deaths"],
            totals["assists"],
            totals["cs"],
            totals["vision"],
            totals["wins"],
        )

    async def get_player_stats(
        self, puuid: str, queue: Optional[int] = None, limit: int = 50
    ) -> MatchStatsResponse:
        """
        Calculate player statistics from recent matches.

        Args:
            puuid: Player PUUID
            queue: Filter by queue ID
            limit: Number of matches to analyze

        Returns:
            MatchStatsResponse with player statistics
        """
        try:
            # Get recent matches for the player
            matches = await self.get_player_matches(puuid, count=limit, queue=queue)

            if not matches.matches:
                return self._create_empty_stats_response(puuid)

            # Get all participants for these matches at once (fixes N+1 query problem)
            match_ids = [m.match_id for m in matches.matches]
            participants_stmt = select(MatchParticipant).where(
                MatchParticipant.match_id.in_(match_ids),
                MatchParticipant.puuid == puuid,
            )
            participants_result = await self.db.execute(participants_stmt)
            participants_by_match = {
                p.match_id: p for p in participants_result.scalars().all()
            }

            # Aggregate statistics
            total_kills, total_deaths, total_assists, total_cs, total_vision, wins = (
                self._aggregate_participant_stats(
                    matches.matches, participants_by_match
                )
            )

            total_matches = len(matches.matches)
            avg_kda = self._calculate_kda(total_kills, total_deaths, total_assists)

            return MatchStatsResponse(
                puuid=puuid,
                total_matches=total_matches,
                wins=wins,
                losses=total_matches - wins,
                win_rate=safe_divide(wins, total_matches),
                avg_kills=safe_divide(total_kills, total_matches),
                avg_deaths=safe_divide(total_deaths, total_matches),
                avg_assists=safe_divide(total_assists, total_matches),
                avg_kda=avg_kda,
                avg_cs=safe_divide(total_cs, total_matches),
                avg_vision_score=safe_divide(total_vision, total_matches),
            )
        except Exception as e:
            logger.error("Failed to get player stats", puuid=puuid, error=str(e))
            raise

    async def _fetch_match_ids_from_api(
        self, riot_api_client, puuid: str, queue: int
    ) -> list[str]:
        """
        Fetch match IDs from Riot API with error handling.

        Raises:
            RateLimitError, NotFoundError: API errors that should propagate
        """
        from ..riot_api.errors import RateLimitError, NotFoundError

        try:
            match_list = await riot_api_client.get_match_list_by_puuid(
                puuid=puuid, queue=queue, start=0, count=100
            )
            return (
                list(match_list.match_ids)
                if match_list and match_list.match_ids
                else []
            )
        except (RateLimitError, NotFoundError) as e:
            logger.warning(
                "Failed to fetch match list",
                puuid=puuid,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def _get_new_match_ids(self, all_match_ids: list[str]) -> list[str]:
        """Filter match IDs to only those not in database."""
        if not all_match_ids:
            return []

        existing_stmt = select(Match.match_id).where(Match.match_id.in_(all_match_ids))
        existing_result = await self.db.execute(existing_stmt)
        existing_match_ids = set(existing_result.scalars().all())

        return [mid for mid in all_match_ids if mid not in existing_match_ids]

    async def _fetch_and_store_single_match(
        self, riot_api_client, match_id: str
    ) -> bool:
        """
        Fetch and store a single match.

        Returns:
            True if successfully stored, False otherwise

        Raises:
            RateLimitError: If rate limit is hit (should stop processing)
        """
        from ..riot_api.errors import RateLimitError

        try:
            match_dto = await riot_api_client.get_match(match_id)
            if match_dto:
                match_data = match_dto.model_dump(by_alias=True, mode="json")
                await self._store_match_detail(match_data)
                return True
            return False
        except RateLimitError:
            logger.warning("Rate limit hit fetching match", match_id=match_id)
            raise
        except Exception as e:
            logger.warning("Failed to fetch match", match_id=match_id, error=str(e))
            return False

    def _validate_platform_code(self, platform: str, puuid: str) -> bool:
        """Validate platform code. Returns True if valid, False if invalid."""
        from ..riot_api.constants import Platform

        try:
            Platform(platform.lower())
            return True
        except ValueError:
            logger.warning("Invalid platform", puuid=puuid, platform=platform)
            return False

    async def _fetch_new_match_ids_for_player(
        self, riot_api_client: "RiotAPIClient", puuid: str, queue: int
    ) -> list[str]:
        """Fetch and filter to only new match IDs."""
        all_match_ids = await self._fetch_match_ids_from_api(
            riot_api_client, puuid, queue
        )
        if not all_match_ids:
            logger.debug("No matches found for player", puuid=puuid)
            return []

        new_match_ids = await self._get_new_match_ids(all_match_ids)
        if not new_match_ids:
            logger.debug("All matches already in database", puuid=puuid)
            return []

        return new_match_ids

    async def fetch_and_store_matches_for_player(
        self,
        riot_api_client: "RiotAPIClient",
        puuid: str,
        count: int = 1,
        queue: int = 420,
        platform: str = "EUN1",
    ) -> int:
        """
        Fetch match history from Riot API and store new matches for a player.

        Used by background jobs only.
        This method checks the database before fetching to avoid duplicate API calls.

        Args:
            riot_api_client: RiotAPIClient instance (from jobs)
            puuid: Player PUUID
            count: Maximum number of NEW matches to fetch (not total matches)
            queue: Queue ID filter (default: 420 = Ranked Solo/Duo)
            platform: Platform ID for the player

        Returns:
            Number of new matches fetched and stored

        Raises:
            RateLimitError: If Riot API rate limit is hit
            AuthenticationError: If API key is invalid
            ForbiddenError: If API key is expired
            ValueError: If invalid platform provided
        """
        try:
            # Validate platform
            if not self._validate_platform_code(platform, puuid):
                return 0

            # Fetch new match IDs
            new_match_ids = await self._fetch_new_match_ids_for_player(
                riot_api_client, puuid, queue
            )
            if not new_match_ids:
                return 0

            # Fetch requested count of new matches
            fetched_count = 0
            for match_id in new_match_ids[:count]:
                if await self._fetch_and_store_single_match(riot_api_client, match_id):
                    fetched_count += 1

            logger.info(
                "Fetched matches for player",
                puuid=puuid,
                count=fetched_count,
                new_matches=len(new_match_ids),
            )
            return fetched_count

        except RiotAPIError:
            # Re-raise RiotAPI errors (rate limits, auth errors, etc.) to caller
            raise
        except Exception as e:
            logger.error("Failed to fetch and store matches", puuid=puuid, error=str(e))
            return 0

    async def _get_matches_from_db(
        self,
        puuid: str,
        start: int,
        count: int,
        queue: Optional[int],
        start_time: Optional[int],
        end_time: Optional[int],
    ) -> List[Match]:
        """Get matches from database."""
        query = (
            select(Match)
            .join(MatchParticipant)
            .where(MatchParticipant.puuid == puuid)
            .order_by(desc(Match.game_creation))
            .offset(start)
            .limit(count)
        )

        if queue:
            query = query.where(Match.queue_id == queue)
        if start_time:
            query = query.where(Match.game_creation >= start_time)
        if end_time:
            query = query.where(Match.game_creation <= end_time)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _count_matches_from_db(
        self,
        puuid: str,
        queue: Optional[int],
        start_time: Optional[int],
        end_time: Optional[int],
    ) -> int:
        """Count total matches for a player from database."""
        query = (
            select(func.count(Match.match_id))
            .join(MatchParticipant)
            .where(MatchParticipant.puuid == puuid)
        )

        if queue:
            query = query.where(Match.queue_id == queue)
        if start_time:
            query = query.where(Match.game_creation >= start_time)
        if end_time:
            query = query.where(Match.game_creation <= end_time)

        result = await self.db.execute(query)
        return result.scalar_one()

    def _get_summoner_name_for_puuid(
        self, puuid: str, participants: List[Dict[str, Any]]
    ) -> str:
        """Extract summoner name for a PUUID from participant data."""
        summoner_name = next(
            (p["summoner_name"] for p in participants if p["puuid"] == puuid),
            None,
        )
        # Ensure summoner_name is never null or empty
        if not summoner_name or summoner_name.strip() == "":
            return "Unknown Player"
        return summoner_name

    async def _ensure_players_exist(
        self,
        participants: List[Dict[str, Any]],
        platform_id: str,
    ) -> None:
        """Ensure all participant players exist in database, creating if needed."""
        # Bulk check for existing players
        participant_puuids = {p["puuid"] for p in participants}
        existing_players_result = await self.db.execute(
            select(Player.puuid).where(Player.puuid.in_(participant_puuids))
        )
        existing_puuids = {row[0] for row in existing_players_result.all()}

        # Bulk create missing players
        missing_puuids = participant_puuids - existing_puuids
        if not missing_puuids:
            return

        new_players = [
            Player(
                puuid=puuid,
                summoner_name=self._get_summoner_name_for_puuid(puuid, participants),
                platform=platform_id.lower(),
                is_active=False,
            )
            for puuid in missing_puuids
        ]

        self.db.add_all(new_players)
        logger.debug("Created minimal player records", count=len(new_players))

    async def _store_match_detail(self, match_data: Dict[str, Any]) -> Match:
        """Store match detail in database."""
        try:
            # Validate match data
            if not self.transformer.validate_match_data(match_data):
                raise ValueError("Invalid match data")

            transformed = self.transformer.transform_match_data(match_data)
            platform_id = transformed["match"].get("platform_id", "EUN1")

            # Ensure all participant players exist
            await self._ensure_players_exist(transformed["participants"], platform_id)

            # Store match and participants
            match = Match(**transformed["match"])
            self.db.add(match)

            participants = [
                MatchParticipant(**p_data) for p_data in transformed["participants"]
            ]
            self.db.add_all(participants)

            await self.db.commit()
            await self.db.refresh(match)

            logger.info("Stored match detail", match_id=match.match_id)
            return match
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to store match detail", error=str(e))
            raise

    def _calculate_kda(self, kills: int, deaths: int, assists: int) -> float:
        """Calculate KDA ratio."""
        from ..utils.statistics import safe_divide

        return safe_divide(kills + assists, deaths, default=float(kills + assists))

    # ============================================
    # Helper Methods for Jobs
    # ============================================

    async def store_match_from_dto(
        self, match_dto: Any, default_platform: str = "EUN1"
    ) -> Match:
        """Store match and participants from Riot API DTO.

        This method handles:
        - Creating Match record
        - Creating MatchParticipant records
        - Ensuring all participant players exist in database

        Args:
            match_dto: Match DTO from Riot API
            default_platform: Default platform if not in DTO

        Returns:
            Stored Match object

        Raises:
            Exception: If storage fails

        Note:
            Caller must commit the transaction.
        """
        from ..schemas.transformers import MatchDTOTransformer

        try:
            # Extract platform
            platform_id = match_dto.info.platform_id or default_platform

            # Create Match record
            match = Match(
                match_id=match_dto.metadata.match_id,
                platform_id=platform_id.upper(),
                game_creation=match_dto.info.game_creation,
                game_duration=match_dto.info.game_duration,
                game_mode=match_dto.info.game_mode,
                game_type=match_dto.info.game_type,
                game_version=match_dto.info.game_version,
                map_id=match_dto.info.map_id,
                queue_id=match_dto.info.queue_id,
            )

            self.db.add(match)

            # Create MatchParticipant records
            for participant in match_dto.info.participants:
                participant_data = MatchDTOTransformer.extract_participant_data(
                    participant
                )
                match_participant = MatchParticipant(
                    match_id=match_dto.metadata.match_id,
                    **participant_data,
                )
                self.db.add(match_participant)

            logger.debug(
                "Stored match from DTO",
                match_id=match_dto.metadata.match_id,
                participant_count=len(match_dto.info.participants),
            )

            return match

        except Exception as e:
            logger.error(
                "Failed to store match from DTO",
                match_id=(
                    match_dto.metadata.match_id
                    if hasattr(match_dto, "metadata")
                    else "unknown"
                ),
                error=str(e),
            )
            raise

    async def count_player_matches(self, puuid: str) -> int:
        """Get count of matches for a player in database.

        Args:
            puuid: Player PUUID

        Returns:
            Number of matches in database
        """
        count_stmt = (
            select(func.count(Match.match_id))
            .join(MatchParticipant, Match.match_id == MatchParticipant.match_id)
            .where(MatchParticipant.puuid == puuid)
        )
        count_result = await self.db.execute(count_stmt)
        return count_result.scalar() or 0

    async def get_player_last_match_time(self, puuid: str) -> Optional[int]:
        """Get timestamp of player's most recent match in database.

        Args:
            puuid: Player PUUID

        Returns:
            Timestamp in milliseconds, or None if no matches
        """
        stmt = (
            select(Match.game_creation)
            .join(MatchParticipant, Match.match_id == MatchParticipant.match_id)
            .where(MatchParticipant.puuid == puuid)
            .order_by(Match.game_creation.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def filter_existing_matches(self, match_ids: List[str]) -> List[str]:
        """Filter out matches that already exist in database.

        Args:
            match_ids: List of match IDs to check

        Returns:
            List of match IDs not in database
        """
        if not match_ids:
            return []

        stmt = select(Match.match_id).where(Match.match_id.in_(match_ids))
        result = await self.db.execute(stmt)
        existing_match_ids = set(result.scalars().all())

        new_match_ids = [mid for mid in match_ids if mid not in existing_match_ids]

        logger.debug(
            "Filtered existing matches",
            total_ids=len(match_ids),
            existing=len(existing_match_ids),
            new=len(new_match_ids),
        )

        return new_match_ids
