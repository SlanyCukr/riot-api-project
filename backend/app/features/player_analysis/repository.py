"""Repository pattern implementation for player_analysis feature.

Provides collection-like interface for accessing player analysis domain objects.
Isolates data access logic from business logic following Martin Fowler's Repository Pattern.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple, Dict, Any

import structlog
from sqlalchemy import select, and_, or_, desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .orm_models import PlayerAnalysisORM
from app.features.players.orm_models import PlayerORM
from app.features.matches.orm_models import MatchORM
from app.features.matches.participants_orm import MatchParticipantORM
from app.features.players.ranks import PlayerRank

logger = structlog.get_logger(__name__)


class PlayerAnalysisRepositoryInterface(ABC):
    """Interface for player analysis repository.

    Defines contract for data access operations.
    Enables mocking and potential swap of implementations (e.g., caching layer).
    """

    @abstractmethod
    async def get_recent_analysis(
        self, puuid: str, hours: int = 24
    ) -> Optional[PlayerAnalysisORM]:
        """Get recent analysis within time window.

        :param puuid: Player's unique identifier
        :param hours: Number of hours to look back for recent analysis
        :returns: PlayerAnalysisORM if found within time window, None otherwise
        """
        pass

    @abstractmethod
    async def get_player_with_relations(self, puuid: str) -> Optional[PlayerORM]:
        """Get player with eager-loaded relationships.

        :param puuid: Player's unique identifier
        :returns: PlayerORM if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_recent_matches(
        self, puuid: str, limit: int = 50
    ) -> List[Tuple[MatchORM, MatchParticipantORM]]:
        """Get recent matches with participant data.

        :param puuid: Player's unique identifier
        :param limit: Maximum number of matches to return
        :returns: List of tuples (MatchORM, MatchParticipantORM)
        """
        pass

    @abstractmethod
    async def get_matches_for_analysis(
        self,
        puuid: str,
        min_games: int,
        queue_filter: Optional[int] = None,
        time_period_days: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Get matches for analysis with filtering.

        Applies filtering at database level for optimal performance.
        Returns pre-filtered match data ready for analysis.

        :param puuid: Player's unique identifier
        :param min_games: Minimum games needed (for limit calculation)
        :param queue_filter: Optional queue type filter
        :param time_period_days: Optional time period filter (days)
        :returns: Tuple of (matches_data_list, match_ids_list)
        """
        pass

    @abstractmethod
    async def create_analysis(self, analysis: PlayerAnalysisORM) -> PlayerAnalysisORM:
        """Create new analysis record.

        :param analysis: PlayerAnalysisORM to create
        :returns: Created analysis with generated fields populated
        """
        pass

    @abstractmethod
    async def mark_matches_processed(self, match_ids: List[str]) -> None:
        """Mark matches as processed for analysis.

        :param match_ids: List of match IDs to mark as processed
        """
        pass

    @abstractmethod
    async def get_current_rank(self, puuid: str) -> Optional[PlayerRank]:
        """Get player's current rank.

        :param puuid: Player's unique identifier
        :returns: PlayerRank if found, None otherwise
        """
        pass


class SQLAlchemyPlayerAnalysisRepository(PlayerAnalysisRepositoryInterface):
    """SQLAlchemy implementation of player analysis repository.

    Handles all database operations for player analysis using SQLAlchemy async sessions.
    Translates repository interface to SQLAlchemy queries.
    """

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session.

        :param db: Async database session
        """
        self.db = db

    async def get_recent_analysis(
        self, puuid: str, hours: int = 24
    ) -> Optional[PlayerAnalysisORM]:
        """Get recent analysis within time window."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        stmt = (
            select(PlayerAnalysisORM)
            .where(
                and_(
                    PlayerAnalysisORM.puuid == puuid,
                    PlayerAnalysisORM.last_analysis >= cutoff_time,
                )
            )
            .order_by(desc(PlayerAnalysisORM.last_analysis))
            .limit(1)
        )

        result = await self.db.execute(stmt)
        analysis = result.scalar_one_or_none()

        if analysis:
            logger.debug(
                "recent_analysis_retrieved",
                puuid=puuid,
                hours=hours,
                analysis_id=analysis.id,
            )

        return analysis

    async def get_player_with_relations(self, puuid: str) -> Optional[PlayerORM]:
        """Get player with eager-loaded relationships."""
        stmt = (
            select(PlayerORM)
            .options(
                selectinload(PlayerORM.ranks),
            )
            .where(PlayerORM.puuid == puuid, PlayerORM.is_active == True)  # noqa: E712
        )

        result = await self.db.execute(stmt)
        player = result.scalar_one_or_none()

        if player:
            logger.debug(
                "player_retrieved_with_relations",
                puuid=puuid,
                riot_id=player.riot_id,
                ranks_count=len(player.ranks) if player.ranks else 0,
            )

        return player

    async def get_recent_matches(
        self, puuid: str, limit: int = 50
    ) -> List[Tuple[MatchORM, MatchParticipantORM]]:
        """Get recent matches with participant data."""
        stmt = (
            select(MatchORM, MatchParticipantORM)
            .join(
                MatchParticipantORM, MatchORM.match_id == MatchParticipantORM.match_id
            )
            .where(MatchParticipantORM.puuid == puuid)
            .order_by(desc(MatchORM.game_creation))
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        matches = list(result)

        logger.debug(
            "recent_matches_retrieved",
            puuid=puuid,
            match_count=len(matches),
            limit=limit,
        )

        return matches

    async def get_matches_for_analysis(
        self,
        puuid: str,
        min_games: int,
        queue_filter: Optional[int] = None,
        time_period_days: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Get matches for analysis with filtering."""
        from datetime import datetime, timedelta, timezone
        from .transformers import PlayerAnalysisTransformer

        # Calculate time cutoff if needed
        cutoff_time_ms = None
        if time_period_days:
            cutoff_time_ms = int(
                (
                    datetime.now(timezone.utc) - timedelta(days=time_period_days)
                ).timestamp()
                * 1000
            )

        # Build query with filters
        stmt = (
            select(MatchORM, MatchParticipantORM)
            .join(
                MatchParticipantORM, MatchORM.match_id == MatchParticipantORM.match_id
            )
            .where(MatchParticipantORM.puuid == puuid)
        )

        # Apply queue filter
        if queue_filter:
            stmt = stmt.where(MatchORM.queue_id == queue_filter)

        # Apply time period filter
        if cutoff_time_ms:
            stmt = stmt.where(MatchORM.game_creation >= cutoff_time_ms)

        # Order by most recent and limit to min_games * 2 for safety
        stmt = stmt.order_by(desc(MatchORM.game_creation)).limit(min_games * 2)

        result = await self.db.execute(stmt)
        raw_matches = list(result)

        # Transform to dict format using transformer
        matches_data: List[Dict[str, Any]] = []
        match_ids: List[str] = []

        for match, participant in raw_matches:
            match_dict = PlayerAnalysisTransformer.match_data_to_dict(
                match, participant
            )
            matches_data.append(match_dict)
            match_ids.append(match.match_id)

        # Log filtering results
        logger.debug(
            "matches_for_analysis_retrieved",
            puuid=puuid,
            total_matches=len(matches_data),
            queue_filter=queue_filter,
            time_period_days=time_period_days,
        )

        return matches_data, match_ids

    async def create_analysis(self, analysis: PlayerAnalysisORM) -> PlayerAnalysisORM:
        """Create new analysis record."""
        self.db.add(analysis)
        await self.db.commit()
        await self.db.refresh(analysis)

        logger.info(
            "analysis_created",
            puuid=analysis.puuid,
            is_smurf=analysis.is_smurf,
            smurf_score=float(analysis.smurf_score),
            confidence=analysis.confidence,
        )

        return analysis

    async def mark_matches_processed(self, match_ids: List[str]) -> None:
        """Mark matches as processed for analysis."""
        if not match_ids:
            logger.debug("no_matches_to_mark", match_ids_count=0)
            return

        try:
            # Update all matches in one query
            stmt = (
                update(MatchORM)
                .where(MatchORM.match_id.in_(match_ids))
                .values(is_processed=True)
            )
            await self.db.execute(stmt)
            await self.db.commit()

            logger.debug(
                "matches_marked_processed",
                match_count=len(match_ids),
                match_ids=match_ids[:5],  # Log first 5 for debugging
            )
        except Exception as e:
            logger.error(
                "failed_to_mark_matches_processed",
                error=str(e),
                match_ids=match_ids,
            )
            # Don't raise - this is not critical for the analysis result
            await self.db.rollback()

    async def get_current_rank(self, puuid: str) -> Optional[PlayerRank]:
        """Get player's current rank."""
        from app.features.players.ranks import PlayerRank as RankModel

        stmt = (
            select(RankModel)
            .where(and_(RankModel.puuid == puuid, RankModel.is_current))
            .limit(1)
        )

        result = await self.db.execute(stmt)
        rank = result.scalar_one_or_none()

        if rank:
            logger.debug(
                "current_rank_retrieved",
                puuid=puuid,
                tier=rank.tier,
                rank=rank.rank,
                queue_type=rank.queue_type,
            )

        return rank

    # ========================================================================
    # ADDITIONAL QUERY METHODS
    # ========================================================================

    async def get_analysis_with_filters(
        self,
        puuid: Optional[str] = None,
        is_smurf: Optional[bool] = None,
        confidence: Optional[str] = None,
        queue_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PlayerAnalysisORM]:
        """Get player analyses with optional filters.

        :param puuid: Filter by player PUUID
        :param is_smurf: Filter by smurf detection status
        :param confidence: Filter by confidence level
        :param queue_type: Filter by queue type
        :param limit: Maximum results to return
        :param offset: Number of results to skip
        :returns: List of matching PlayerAnalysisORM records
        """
        stmt = select(PlayerAnalysisORM)

        conditions = []
        if puuid:
            conditions.append(PlayerAnalysisORM.puuid == puuid)
        if is_smurf is not None:
            conditions.append(PlayerAnalysisORM.is_smurf == is_smurf)
        if confidence:
            conditions.append(PlayerAnalysisORM.confidence == confidence)
        if queue_type:
            conditions.append(PlayerAnalysisORM.queue_type == queue_type)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = (
            stmt.order_by(desc(PlayerAnalysisORM.last_analysis))
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        analyses = list(result.scalars().all())

        logger.debug(
            "analysis_list_retrieved",
            count=len(analyses),
            puuid=puuid,
            is_smurf=is_smurf,
            confidence=confidence,
        )

        return analyses

    async def get_analyses_for_ban_check(
        self, cutoff: datetime, limit: int
    ) -> List[PlayerAnalysisORM]:
        """Get analyses needing ban status check.

        Join query with Player to find analyses marked as smurfs
        where the player needs a ban status check.

        :param cutoff: DateTime threshold for last ban check
        :param limit: Maximum number of analyses to return
        :returns: List of PlayerAnalysisORM needing ban check
        """
        stmt = (
            select(PlayerAnalysisORM)
            .join(PlayerORM, PlayerORM.puuid == PlayerAnalysisORM.puuid)
            .where(
                PlayerAnalysisORM.is_smurf == True,  # noqa: E712
                or_(
                    PlayerORM.last_ban_check.is_(None),
                    PlayerORM.last_ban_check < cutoff,
                ),
            )
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        analyses = list(result.scalars().all())

        logger.debug(
            "analyses_for_ban_check_retrieved",
            count=len(analyses),
            cutoff=cutoff,
        )

        return analyses

    async def update_analysis(self, analysis: PlayerAnalysisORM) -> PlayerAnalysisORM:
        """Update existing analysis record.

        :param analysis: PlayerAnalysisORM with updates
        :returns: Updated analysis with refreshed state
        """
        await self.db.commit()
        await self.db.refresh(analysis)

        logger.debug(
            "analysis_updated",
            puuid=analysis.puuid,
            analysis_id=analysis.id,
        )

        return analysis

    async def delete_analysis(self, analysis: PlayerAnalysisORM) -> None:
        """Delete analysis record.

        :param analysis: PlayerAnalysisORM to delete
        """
        await self.db.delete(analysis)
        await self.db.commit()

        logger.info(
            "analysis_deleted",
            puuid=analysis.puuid,
            analysis_id=analysis.id,
        )

    async def get_match_count_for_player(
        self, puuid: str, queue_filter: Optional[int] = None
    ) -> int:
        """Get total match count for a player.

        :param puuid: Player's unique identifier
        :param queue_filter: Optional queue type filter
        :returns: Total number of matches for the player
        """
        stmt = (
            select(MatchParticipantORM)
            .join(MatchORM, MatchORM.match_id == MatchParticipantORM.match_id)
            .where(MatchParticipantORM.puuid == puuid)
        )

        if queue_filter:
            stmt = stmt.where(MatchORM.queue_id == queue_filter)

        result = await self.db.execute(stmt)
        matches = list(result.scalars().all())

        count = len(matches)

        logger.debug(
            "match_count_retrieved",
            puuid=puuid,
            count=count,
            queue_filter=queue_filter,
        )

        return count
