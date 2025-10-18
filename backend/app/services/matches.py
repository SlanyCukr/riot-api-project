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

            # Calculate statistics
            total_kills = 0
            total_deaths = 0
            total_assists = 0
            total_cs = 0
            total_vision = 0
            wins = 0

            for match in matches.matches:
                # Get participant data from pre-fetched results
                participant = participants_by_match.get(match.match_id)
                if participant:
                    total_kills += participant.kills
                    total_deaths += participant.deaths
                    total_assists += participant.assists
                    total_cs += participant.cs
                    total_vision += participant.vision_score
                    if participant.win:
                        wins += 1

            total_matches = len(matches.matches)
            avg_kda = self._calculate_kda(total_kills, total_deaths, total_assists)

            return MatchStatsResponse(
                puuid=puuid,
                total_matches=total_matches,
                wins=wins,
                losses=total_matches - wins,
                win_rate=wins / total_matches if total_matches > 0 else 0.0,
                avg_kills=total_kills / total_matches if total_matches > 0 else 0.0,
                avg_deaths=total_deaths / total_matches if total_matches > 0 else 0.0,
                avg_assists=total_assists / total_matches if total_matches > 0 else 0.0,
                avg_kda=avg_kda,
                avg_cs=total_cs / total_matches if total_matches > 0 else 0.0,
                avg_vision_score=(
                    total_vision / total_matches if total_matches > 0 else 0.0
                ),
            )
        except Exception as e:
            logger.error("Failed to get player stats", puuid=puuid, error=str(e))
            raise

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
        from ..riot_api.constants import Platform
        from ..riot_api.errors import (
            RateLimitError,
            NotFoundError,
            AuthenticationError,
            ForbiddenError,
        )

        try:
            # Validate platform
            try:
                Platform(platform.lower())
            except ValueError:
                logger.warning("Invalid platform", puuid=puuid, platform=platform)
                return 0

            # Get match list from Riot API (just IDs - cheap operation)
            try:
                match_list = await riot_api_client.get_match_list_by_puuid(
                    puuid=puuid,
                    queue=queue,
                    start=0,
                    count=100,  # Get more IDs to filter through
                )
            except (RateLimitError, NotFoundError) as e:
                logger.warning(
                    "Failed to fetch match list",
                    puuid=puuid,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise

            if not match_list or not match_list.match_ids:
                logger.debug("No matches found for player", puuid=puuid)
                return 0

            # Check which matches already exist in database
            existing_stmt = select(Match.match_id).where(
                Match.match_id.in_(list(match_list.match_ids))
            )
            existing_result = await self.db.execute(existing_stmt)
            existing_match_ids = set(existing_result.scalars().all())

            # Filter to only new matches
            new_match_ids = [
                mid for mid in match_list.match_ids if mid not in existing_match_ids
            ]

            if not new_match_ids:
                logger.debug("All matches already in database", puuid=puuid)
                return 0

            # Fetch only the requested count of new matches
            matches_to_fetch = new_match_ids[:count]
            fetched_count = 0

            for match_id in matches_to_fetch:
                try:
                    # Fetch match details from Riot API
                    match_dto = await riot_api_client.get_match(match_id)

                    if match_dto:
                        # Store using existing method
                        match_data = match_dto.model_dump(by_alias=True, mode="json")
                        await self._store_match_detail(match_data)
                        fetched_count += 1

                except RateLimitError:
                    logger.warning("Rate limit hit fetching match", match_id=match_id)
                    raise  # Propagate to stop processing
                except Exception as e:
                    logger.warning(
                        "Failed to fetch match", match_id=match_id, error=str(e)
                    )
                    continue

            logger.info(
                "Fetched matches for player",
                puuid=puuid,
                count=fetched_count,
                new_matches=len(new_match_ids),
            )
            return fetched_count

        except RateLimitError:
            raise  # Propagate rate limit errors
        except (AuthenticationError, ForbiddenError):
            raise  # Propagate authentication errors so jobs fail
        except Exception as e:
            logger.error(
                "Failed to fetch and store matches",
                puuid=puuid,
                error=str(e),
            )
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

    async def _store_match_detail(self, match_data: Dict[str, Any]) -> Match:
        """Store match detail in database."""
        try:
            # Validate match data
            if not self.transformer.validate_match_data(match_data):
                raise ValueError("Invalid match data")

            transformed = self.transformer.transform_match_data(match_data)

            # Get platform from match metadata
            platform_id = transformed["match"].get("platform_id", "EUN1")

            # Ensure all participant PUUIDs exist in players table
            # Bulk check for existing players
            participant_puuids = {p["puuid"] for p in transformed["participants"]}
            existing_players_result = await self.db.execute(
                select(Player.puuid).where(Player.puuid.in_(participant_puuids))
            )
            existing_puuids = {row[0] for row in existing_players_result.all()}

            # Bulk create missing players
            missing_puuids = participant_puuids - existing_puuids
            if missing_puuids:
                new_players = []
                for puuid in missing_puuids:
                    # Get summoner name from participants
                    summoner_name = next(
                        (
                            p["summoner_name"]
                            for p in transformed["participants"]
                            if p["puuid"] == puuid
                        ),
                        None,
                    )
                    # Ensure summoner_name is never null or empty
                    if not summoner_name or summoner_name.strip() == "":
                        summoner_name = (
                            "Unknown Player"  # Fallback for missing summoner name
                        )

                    new_players.append(
                        Player(
                            puuid=puuid,
                            summoner_name=summoner_name,
                            platform=platform_id.lower(),
                            is_active=False,
                        )
                    )

                self.db.add_all(new_players)
                logger.debug(
                    "Created minimal player records",
                    count=len(new_players),
                )

            # Store match
            match_data_dict = transformed["match"]
            match = Match(**match_data_dict)
            self.db.add(match)

            # Bulk store participants
            participants = [
                MatchParticipant(**participant_data)
                for participant_data in transformed["participants"]
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
        if deaths == 0:
            return float(kills + assists)
        return (kills + assists) / deaths

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
