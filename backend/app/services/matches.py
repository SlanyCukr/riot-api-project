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
                # Fetch from API
                api_matches = await self._fetch_matches_from_api(
                    puuid, start, count, queue, start_time, end_time
                )
                # Store in database
                await self._store_matches(api_matches)

            # Return combined results
            all_matches = await self._get_matches_from_db(
                puuid, start, count, queue, start_time, end_time
            )

            match_responses = [
                MatchResponse.model_validate(match) for match in all_matches
            ]

            return MatchListResponse(
                matches=match_responses,
                total=len(match_responses),
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
        """Store match details in database."""
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
            participant_puuids = {p["puuid"] for p in transformed["participants"]}
            for puuid in participant_puuids:
                # Check if player exists
                existing_player = await self.db.execute(
                    select(Player).where(Player.puuid == puuid)
                )
                if not existing_player.scalar_one_or_none():
                    # Create minimal player record
                    # Get summoner name from participants
                    summoner_name = next(
                        (
                            p["summoner_name"]
                            for p in transformed["participants"]
                            if p["puuid"] == puuid
                        ),
                        "Unknown",
                    )
                    player = Player(
                        puuid=puuid,
                        summoner_name=summoner_name,
                        platform=platform_id.lower(),
                        is_active=True,
                    )
                    self.db.add(player)
                    logger.debug(
                        "Created minimal player record",
                        puuid=puuid,
                        summoner_name=summoner_name,
                    )

            # Store match
            match_data_dict = transformed["match"]
            match = Match(**match_data_dict)
            self.db.add(match)

            # Store participants
            for participant_data in transformed["participants"]:
                participant = MatchParticipant(**participant_data)
                self.db.add(participant)

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
