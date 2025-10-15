"""Match service for handling match data operations."""

from typing import Optional, List, Dict, Any
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, ColumnElement
from sqlalchemy.orm import selectinload

from ..riot_api.data_manager import RiotDataManager
from ..models.matches import Match
from ..models.participants import MatchParticipant
from ..models.players import Player
from ..schemas.matches import MatchResponse, MatchListResponse, MatchStatsResponse
from ..riot_api.transformers import MatchTransformer

logger = structlog.get_logger(__name__)


class MatchService:
    """Service for handling match data operations."""

    def __init__(self, db: AsyncSession, data_manager: RiotDataManager):
        """Initialize match service."""
        self.db = db
        self.data_manager = data_manager
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
        Get match history for a player.

        Args:
            puuid: Player PUUID
            start: Start index for pagination
            count: Number of matches to return
            queue: Filter by queue ID
            start_time: Start timestamp
            end_time: End timestamp

        Returns:
            MatchListResponse with matches
        """
        try:
            # First try to get from database
            db_matches = await self._get_matches_from_db(
                puuid, start, count, queue, start_time, end_time
            )

            if len(db_matches) < count:
                # Fetch from API (cap at 100 due to Riot API limit)
                # We fetch more than what we have in DB, but not more than what user requested
                fetch_count = min(count - len(db_matches), 100)
                fetch_start = start + len(db_matches)

                api_matches = await self._fetch_matches_from_api(
                    puuid, fetch_start, fetch_count, queue, start_time, end_time
                )
                # Store in database
                await self._store_matches(api_matches)

            # Return combined results
            all_matches = await self._get_matches_from_db(
                puuid, start, count, queue, start_time, end_time
            )

            # Get total count of matches for pagination
            total_count = await self._count_matches_from_db(
                puuid, queue, start_time, end_time
            )

            match_responses = [
                MatchResponse.model_validate(match) for match in all_matches
            ]

            return MatchListResponse(
                matches=match_responses,
                total=total_count,
                start=start,
                count=count,
            )
        except Exception as e:
            logger.error("Failed to get player matches", puuid=puuid, error=str(e))
            raise

    async def get_match_details(self, match_id: str) -> Optional[MatchResponse]:
        """
        Get detailed match information.

        Args:
            match_id: Match ID

        Returns:
            MatchResponse with detailed information
        """
        try:
            # Try database first
            match = await self._get_match_from_db(match_id)
            if not match:
                # Fetch from API using RiotDataManager
                match_data = await self.data_manager.get_match(match_id)
                # Convert MatchDTO to dict for storage
                match_data_dict = match_data.model_dump(by_alias=True, mode="json")
                match = await self._store_match_detail(match_data_dict)

            return MatchResponse.model_validate(match)
        except Exception as e:
            logger.error("Failed to get match details", match_id=match_id, error=str(e))
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

            # Calculate statistics
            total_kills = 0
            total_deaths = 0
            total_assists = 0
            total_cs = 0
            total_vision = 0
            wins = 0

            for match in matches.matches:
                # Get participant data for this player
                participant = await self._get_match_participant(match.match_id, puuid)
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

    async def get_player_encounters(self, puuid: str, limit: int = 20) -> List[str]:
        """
        Get players encountered with/against in recent matches.

        Args:
            puuid: Player PUUID
            limit: Number of matches to check

        Returns:
            List of encountered player PUUIDs
        """
        try:
            matches = await self.get_player_matches(puuid, count=limit)
            encountered_puuids: set[str] = set()

            for match in matches.matches:
                participants = await self._get_match_participants(match.match_id)
                for participant in participants:
                    if str(participant.puuid) != puuid:
                        encountered_puuids.add(str(participant.puuid))

            return list(encountered_puuids)
        except Exception as e:
            logger.error("Failed to get player encounters", puuid=puuid, error=str(e))
            raise

    async def fetch_and_store_matches_for_player(
        self,
        puuid: str,
        count: int = 1,
        queue: int = 420,
        platform: str = "EUN1",
    ) -> int:
        """
        Fetch match history from Riot API and store new matches for a player.

        This method checks the database before fetching to avoid duplicate API calls.

        Args:
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
        from ..riot_api.endpoints import Platform
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
                match_list = await self.data_manager.api_client.get_match_list_by_puuid(
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
                    match_dto = await self.data_manager.api_client.get_match(match_id)

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

    async def _fetch_matches_from_api(
        self,
        puuid: str,
        start: int,
        count: int,
        queue: Optional[int],
        start_time: Optional[int],
        end_time: Optional[int],
    ) -> List[str]:
        """Fetch match IDs from Riot API using API client."""
        try:
            match_list = await self.data_manager.api_client.get_match_list_by_puuid(
                puuid=puuid,
                start=start,
                count=count,
                queue=queue,
                start_time=start_time,
                end_time=end_time,
            )
            return match_list.match_ids
        except Exception as e:
            logger.error("Failed to fetch matches from API", puuid=puuid, error=str(e))
            raise

    async def _store_matches(self, match_ids: List[str]) -> None:
        """Store match details in database sequentially to avoid transaction conflicts."""
        for match_id in match_ids:
            try:
                # Check if match already exists
                existing_match = await self._get_match_from_db(match_id)
                if existing_match:
                    continue

                match_dto = await self.data_manager.get_match(match_id)
                # Convert MatchDTO to dict for storage - use model_dump with by_alias=True
                # to get camelCase field names that the transformer expects
                match_data = match_dto.model_dump(by_alias=True, mode="json")
                await self._store_match_detail(match_data)
            except Exception as e:
                logger.error("Failed to store match", match_id=match_id, error=str(e))
                # Continue with next match instead of failing the entire batch
                continue

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
                            is_active=True,
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

    async def _get_match_from_db(self, match_id: str) -> Optional[Match]:
        """Get match from database."""
        query = select(Match).where(Match.match_id == match_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_match_participant(
        self, match_id: str, puuid: str
    ) -> Optional[MatchParticipant]:
        """Get match participant from database."""
        query = select(MatchParticipant).where(
            and_(MatchParticipant.match_id == match_id, MatchParticipant.puuid == puuid)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_match_participants(self, match_id: str) -> List[MatchParticipant]:
        """Get all match participants from database."""
        query = select(MatchParticipant).where(MatchParticipant.match_id == match_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    def _calculate_kda(self, kills: int, deaths: int, assists: int) -> float:
        """Calculate KDA ratio."""
        if deaths == 0:
            return float(kills + assists)
        return (kills + assists) / deaths

    async def search_matches(
        self,
        puuid: Optional[str] = None,
        queue_id: Optional[int] = None,
        game_mode: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        champion_id: Optional[int] = None,
        is_processed: Optional[bool] = None,
        page: int = 1,
        size: int = 20,
    ) -> Dict[str, Any]:
        """
        Search matches with various filters.

        Args:
            puuid: Filter by player PUUID
            queue_id: Filter by queue ID
            game_mode: Filter by game mode
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            champion_id: Filter by champion ID
            is_processed: Filter by processing status
            page: Page number
            size: Page size

        Returns:
            Dictionary with search results
        """
        try:
            offset = (page - 1) * size
            query = select(Match)
            count_query = select(func.count(Match.match_id))

            # Determine if participant filters are needed
            needs_participant_join = puuid or champion_id

            if needs_participant_join:
                # Join once and apply all participant filters
                query = query.join(MatchParticipant)
                count_query = count_query.join(MatchParticipant)

                participant_conditions: List[ColumnElement[bool]] = []
                if puuid:
                    participant_conditions.append(MatchParticipant.puuid == puuid)
                if champion_id:
                    participant_conditions.append(
                        MatchParticipant.champion_id == champion_id
                    )

                query = query.where(and_(*participant_conditions))
                count_query = count_query.where(and_(*participant_conditions))

            # Apply match-level filters (no join needed)
            if queue_id:
                query = query.where(Match.queue_id == queue_id)
                count_query = count_query.where(Match.queue_id == queue_id)
            if game_mode:
                query = query.where(Match.game_mode == game_mode)
                count_query = count_query.where(Match.game_mode == game_mode)
            if start_time:
                query = query.where(Match.game_creation >= start_time)
                count_query = count_query.where(Match.game_creation >= start_time)
            if end_time:
                query = query.where(Match.game_creation <= end_time)
                count_query = count_query.where(Match.game_creation <= end_time)
            if is_processed is not None:
                query = query.where(Match.is_processed == is_processed)
                count_query = count_query.where(Match.is_processed == is_processed)

            # Get total count
            total_result = await self.db.execute(count_query)
            total = total_result.scalar()
            total = total if total is not None else 0

            # Get paginated results
            query = query.order_by(desc(Match.game_creation)).offset(offset).limit(size)
            result = await self.db.execute(query)
            matches = result.scalars().all()

            match_responses = [MatchResponse.model_validate(match) for match in matches]

            return {
                "matches": match_responses,
                "total": total,
                "page": page,
                "size": size,
                "pages": (total + size - 1) // size,
            }
        except Exception as e:
            logger.error("Failed to search matches", error=str(e))
            raise

    async def get_match_by_id_with_participants(
        self, match_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get match with all participant details.

        Args:
            match_id: Match ID

        Returns:
            Dictionary with match and participant data
        """
        try:
            query = (
                select(Match)
                .options(selectinload(Match.participants))
                .where(Match.match_id == match_id)
            )
            result = await self.db.execute(query)
            match = result.scalar_one_or_none()

            if not match:
                return None

            return {
                "match": MatchResponse.model_validate(match),
                "participants": [
                    participant.to_dict() for participant in match.participants
                ],
            }
        except Exception as e:
            logger.error(
                "Failed to get match with participants", match_id=match_id, error=str(e)
            )
            raise

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
