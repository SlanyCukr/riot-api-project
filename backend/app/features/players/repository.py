"""Repository pattern implementation for players feature.

Provides collection-like interface for accessing player domain objects.
Isolates data access logic from business logic following Martin Fowler's Repository Pattern.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy import select, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .orm_models import PlayerORM, PlayerRankORM

logger = structlog.get_logger(__name__)


class PlayerRepositoryInterface(ABC):
    """Interface for player repository.

    Defines contract for data access operations.
    Enables mocking and potential swap of implementations (e.g., caching layer).
    """

    @abstractmethod
    async def get_by_puuid(self, puuid: str) -> Optional[PlayerORM]:
        """Get player by PUUID with eager-loaded relationships.

        :param puuid: Player's unique identifier
        :returns: PlayerORM if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_riot_id(
        self, game_name: str, tag_line: str, platform: str
    ) -> Optional[PlayerORM]:
        """Find player by Riot ID (exact match).

        :param game_name: Riot ID game name
        :param tag_line: Riot ID tag line
        :param platform: Platform region
        :returns: PlayerORM if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_summoner_name(
        self, summoner_name: str, platform: str
    ) -> list[PlayerORM]:
        """Find players by summoner name (fuzzy match with ILIKE).

        :param summoner_name: Summoner name to search
        :param platform: Platform region
        :returns: List of matching players (limited to 10)
        """
        pass

    @abstractmethod
    async def get_tracked_players(self) -> list[PlayerORM]:
        """Get all tracked players ordered by summoner name.

        :returns: List of tracked players
        """
        pass

    @abstractmethod
    async def get_players_needing_refresh(
        self, days_since_update: int, limit: int
    ) -> list[PlayerORM]:
        """Get players with stale data that need refresh.

        :param days_since_update: Age threshold in days
        :param limit: Maximum number of players to return
        :returns: List of players with stale data
        """
        pass

    @abstractmethod
    async def create(self, player: PlayerORM) -> PlayerORM:
        """Add new player to repository.

        :param player: Player domain object to add
        :returns: Created player with generated fields populated
        """
        pass

    @abstractmethod
    async def save(self, player: PlayerORM) -> PlayerORM:
        """Save existing player changes.

        :param player: Player domain object with changes
        :returns: Updated player with refreshed state
        """
        pass

    @abstractmethod
    async def delete(self, player: PlayerORM) -> None:
        """Remove player from repository (soft delete).

        :param player: Player to delete
        """
        pass

    @abstractmethod
    async def search_all_players(
        self, platform: str, search_pattern: str, limit: int
    ) -> list[PlayerORM]:
        """Search players by any field for fuzzy matching.

        :param platform: Platform region
        :param search_pattern: SQL ILIKE pattern to search
        :param limit: Maximum results to return
        :returns: List of matching players
        """
        pass

    @abstractmethod
    async def get_recent_opponents(self, puuid: str, limit: int) -> list[PlayerORM]:
        """Get recent opponents for a player with join query.

        Complex query with MatchParticipant joins.

        :param puuid: Player's PUUID
        :param limit: Maximum opponents to return
        :returns: List of opponent players
        """
        pass

    @abstractmethod
    async def fuzzy_search_by_type(
        self,
        platform: str,
        search_type: str,
        query_lower: str,
        game_name: str | None,
        tag_line: str | None,
        limit: int,
    ) -> list[PlayerORM]:
        """Fuzzy search players with type-specific query logic.

        :param platform: Platform region
        :param search_type: Type of search ("riot_id", "tag", "name", "all")
        :param query_lower: Lowercased search query
        :param game_name: Parsed game name (for riot_id searches)
        :param tag_line: Parsed tag line (for tag/riot_id searches)
        :param limit: Maximum results to return
        :returns: List of matching players
        """
        pass

    @abstractmethod
    async def get_players_needing_matches(
        self, target_matches: int, limit: int
    ) -> list[PlayerORM]:
        """Get discovered players with insufficient match history.

        Complex query with MatchParticipant join and aggregation.

        :param target_matches: Target number of matches per player
        :param limit: Maximum players to return
        :returns: List of players with insufficient matches
        """
        pass

    @abstractmethod
    async def get_players_ready_for_analysis(
        self, min_matches: int, limit: int
    ) -> list[PlayerORM]:
        """Get unanalyzed players with sufficient match history.

        Complex query with MatchParticipant join, PlayerAnalysis outer join,
        and aggregation.

        :param min_matches: Minimum number of matches required
        :param limit: Maximum players to return
        :returns: List of players ready for analysis
        """
        pass

    @abstractmethod
    async def get_players_for_ban_check(
        self, cutoff: datetime, limit: int
    ) -> list[PlayerORM]:
        """Get detected smurfs needing ban status check.

        Join query with PlayerAnalysis to find players with is_smurf=True
        and stale or missing ban check timestamps.

        :param cutoff: DateTime threshold for last ban check
        :param limit: Maximum players to return
        :returns: List of players needing ban check
        """
        pass

    @abstractmethod
    async def create_rank(self, rank: "PlayerRankORM") -> "PlayerRankORM":
        """Create new rank record for a player.

        :param rank: Rank domain object to create
        :returns: Created rank with generated fields populated
        """
        pass

    @abstractmethod
    async def get_rank_by_puuid(
        self, puuid: str, queue_type: str
    ) -> Optional["PlayerRankORM"]:
        """Get most recent rank for a player by queue type.

        :param puuid: Player's PUUID
        :param queue_type: Queue type (e.g., RANKED_SOLO_5x5)
        :returns: Most recent rank or None if no rank data exists
        """
        pass


class SQLAlchemyPlayerRepository(PlayerRepositoryInterface):
    """SQLAlchemy implementation of player repository.

    Handles all database operations for players using SQLAlchemy async sessions.
    Translates repository interface to SQLAlchemy queries.
    """

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session.

        :param db: Async database session
        """
        self.db = db

    async def get_by_puuid(self, puuid: str) -> Optional[PlayerORM]:
        """Get player by PUUID with eager-loaded relationships."""
        stmt = (
            select(PlayerORM)
            .options(
                selectinload(PlayerORM.ranks),
                # Add other relationships as needed for your use case
            )
            .where(PlayerORM.puuid == puuid, PlayerORM.is_active == True)  # noqa: E712
        )

        result = await self.db.execute(stmt)
        player = result.scalar_one_or_none()

        if player:
            logger.debug("player_retrieved", puuid=puuid, riot_id=player.riot_id)

        return player

    async def find_by_riot_id(
        self, game_name: str, tag_line: str, platform: str
    ) -> Optional[PlayerORM]:
        """Find player by Riot ID (exact match)."""
        stmt = (
            select(PlayerORM)
            .options(selectinload(PlayerORM.ranks))
            .where(
                PlayerORM.riot_id == game_name,
                PlayerORM.tag_line == tag_line,
                PlayerORM.platform == platform.upper(),
                PlayerORM.is_active == True,  # noqa: E712
            )
        )

        result = await self.db.execute(stmt)
        player = result.scalar_one_or_none()

        logger.debug(
            "player_search_by_riot_id",
            game_name=game_name,
            tag_line=tag_line,
            platform=platform,
            found=player is not None,
        )

        return player

    async def find_by_summoner_name(
        self, summoner_name: str, platform: str
    ) -> list[PlayerORM]:
        """Find players by summoner name (fuzzy match with ILIKE)."""
        stmt = (
            select(PlayerORM)
            .options(selectinload(PlayerORM.ranks))
            .where(
                PlayerORM.summoner_name.ilike(f"%{summoner_name}%"),
                PlayerORM.platform == platform.upper(),
                PlayerORM.is_active == True,  # noqa: E712
            )
            .limit(10)  # Prevent excessive results
        )

        result = await self.db.execute(stmt)
        players = list(result.scalars().all())

        logger.debug(
            "player_search_by_summoner_name",
            summoner_name=summoner_name,
            platform=platform,
            results_count=len(players),
        )

        return players

    async def get_tracked_players(self) -> list[PlayerORM]:
        """Get all tracked players ordered by summoner name."""
        stmt = (
            select(PlayerORM)
            .options(selectinload(PlayerORM.ranks))
            .where(
                PlayerORM.is_tracked == True,  # noqa: E712
                PlayerORM.is_active == True,  # noqa: E712
            )
            .order_by(PlayerORM.summoner_name)
        )

        result = await self.db.execute(stmt)
        players = list(result.scalars().all())

        logger.info("tracked_players_retrieved", count=len(players))

        return players

    async def get_players_needing_refresh(
        self, days_since_update: int, limit: int
    ) -> list[PlayerORM]:
        """Get players with stale data."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_since_update)

        stmt = (
            select(PlayerORM)
            .options(selectinload(PlayerORM.ranks))
            .where(
                PlayerORM.is_tracked == True,  # noqa: E712
                PlayerORM.is_active == True,  # noqa: E712
                PlayerORM.updated_at < cutoff,
            )
            .order_by(PlayerORM.updated_at.asc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        players = list(result.scalars().all())

        logger.debug(
            "players_needing_refresh",
            days_threshold=days_since_update,
            count=len(players),
        )

        return players

    async def create(self, player: PlayerORM) -> PlayerORM:
        """Create new player record."""
        self.db.add(player)
        await self.db.commit()
        await self.db.refresh(player)

        logger.info(
            "player_created",
            puuid=player.puuid,
            riot_id=player.riot_id,
            platform=player.platform,
        )

        return player

    async def save(self, player: PlayerORM) -> PlayerORM:
        """Save existing player changes."""
        await self.db.commit()
        await self.db.refresh(player)

        logger.debug("player_saved", puuid=player.puuid)

        return player

    async def delete(self, player: PlayerORM) -> None:
        """Soft delete player."""
        player.is_active = False
        await self.db.commit()

        logger.info("player_deleted", puuid=player.puuid)

    async def search_all_players(
        self, platform: str, search_pattern: str, limit: int
    ) -> list[PlayerORM]:
        """Search players by any field for fuzzy matching."""
        stmt = (
            select(PlayerORM)
            .options(selectinload(PlayerORM.ranks))
            .where(
                PlayerORM.platform == platform.upper(),
                PlayerORM.is_active == True,  # noqa: E712
                or_(
                    PlayerORM.summoner_name.ilike(search_pattern),
                    PlayerORM.riot_id.ilike(search_pattern),
                    PlayerORM.tag_line.ilike(search_pattern),
                ),
            )
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        players = list(result.scalars().all())

        logger.debug(
            "fuzzy_search_executed",
            platform=platform,
            pattern=search_pattern,
            results=len(players),
        )

        return players

    async def get_recent_opponents(self, puuid: str, limit: int) -> list[PlayerORM]:
        """Get recent opponents for a player with join query."""
        from app.features.matches.participants import MatchParticipant

        # Subquery: Get recent matches for the player
        recent_matches_subq = (
            select(MatchParticipant.match_id)
            .where(MatchParticipant.puuid == puuid)
            .order_by(MatchParticipant.id.desc())
            .limit(limit * 5)  # Get more matches to find enough opponents
            .subquery()
        )

        # Main query: Get opponents from those matches
        stmt = (
            select(PlayerORM)
            .options(selectinload(PlayerORM.ranks))
            .join(MatchParticipant, PlayerORM.puuid == MatchParticipant.puuid)
            .where(
                MatchParticipant.match_id.in_(select(recent_matches_subq)),
                MatchParticipant.puuid != puuid,
                PlayerORM.is_active == True,  # noqa: E712
                PlayerORM.summoner_name.isnot(None),
                PlayerORM.summoner_name != "",
            )
            .distinct()
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        opponents = list(result.scalars().all())

        logger.debug(
            "recent_opponents_retrieved",
            puuid=puuid,
            opponent_count=len(opponents),
            limit=limit,
        )

        return opponents

    async def fuzzy_search_by_type(
        self,
        platform: str,
        search_type: str,
        query_lower: str,
        game_name: str | None,
        tag_line: str | None,
        limit: int,
    ) -> list[PlayerORM]:
        """Fuzzy search players with type-specific query logic.

        Builds different queries based on search type:
        - "riot_id": Exact or partial Riot ID match
        - "tag": Tag-only search
        - "name" or "all": Search summoner names and riot_id
        """
        # Build query based on search type
        if search_type == "riot_id" and game_name and tag_line:
            # Search for exact or partial Riot ID
            stmt = (
                select(PlayerORM)
                .options(selectinload(PlayerORM.ranks))
                .where(
                    PlayerORM.platform == platform.upper(),
                    PlayerORM.is_active == True,  # noqa: E712
                    or_(
                        # Exact match
                        and_(
                            PlayerORM.riot_id.ilike(game_name),
                            PlayerORM.tag_line.ilike(tag_line),
                        ),
                        # Partial matches
                        PlayerORM.riot_id.ilike(f"%{game_name}%"),
                        PlayerORM.tag_line.ilike(f"%{tag_line}%"),
                    ),
                )
                .limit(limit)
            )
        elif search_type == "tag" and tag_line:
            # Search tags only
            stmt = (
                select(PlayerORM)
                .options(selectinload(PlayerORM.ranks))
                .where(
                    PlayerORM.platform == platform.upper(),
                    PlayerORM.is_active == True,  # noqa: E712
                    PlayerORM.tag_line.ilike(f"%{tag_line}%"),
                )
                .limit(limit)
            )
        else:
            # name or all - search summoner names and riot_id
            search_term = game_name if game_name else query_lower
            stmt = (
                select(PlayerORM)
                .options(selectinload(PlayerORM.ranks))
                .where(
                    PlayerORM.platform == platform.upper(),
                    PlayerORM.is_active == True,  # noqa: E712
                    or_(
                        PlayerORM.summoner_name.ilike(f"%{search_term}%"),
                        PlayerORM.riot_id.ilike(f"%{search_term}%"),
                    ),
                )
                .limit(limit)
            )

        result = await self.db.execute(stmt)
        players = list(result.scalars().all())

        logger.debug(
            "fuzzy_search_by_type_executed",
            platform=platform,
            search_type=search_type,
            results_count=len(players),
        )

        return players

    async def get_players_needing_matches(
        self, target_matches: int, limit: int
    ) -> list[PlayerORM]:
        """Get discovered players with insufficient match history.

        Complex query with left outer join to MatchParticipant,
        group by, and having clause for aggregation.
        """
        from app.features.matches.participants import MatchParticipant

        stmt = (
            select(PlayerORM)
            .options(selectinload(PlayerORM.ranks))
            .join(
                MatchParticipant,
                PlayerORM.puuid == MatchParticipant.puuid,
                isouter=True,
            )
            .where(
                PlayerORM.is_tracked == False,  # noqa: E712
                PlayerORM.is_active == True,  # noqa: E712
                PlayerORM.matches_exhausted == False,  # noqa: E712
            )
            .group_by(PlayerORM.puuid)
            .having(func.count(MatchParticipant.match_id) < target_matches)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        players = list(result.scalars().all())

        logger.debug(
            "players_needing_matches_retrieved",
            count=len(players),
            target_matches=target_matches,
        )

        return players

    async def get_players_ready_for_analysis(
        self, min_matches: int, limit: int
    ) -> list[PlayerORM]:
        """Get unanalyzed players with sufficient match history.

        Complex query with MatchParticipant join, PlayerAnalysis outer join,
        and aggregation to find players ready for analysis.
        """
        from app.features.matches.participants import MatchParticipant
        from app.features.player_analysis.orm_models import (
            PlayerAnalysisORM as PlayerAnalysis,
        )

        stmt = (
            select(PlayerORM)
            .options(selectinload(PlayerORM.ranks))
            .join(MatchParticipant, PlayerORM.puuid == MatchParticipant.puuid)
            .outerjoin(PlayerAnalysis, PlayerORM.puuid == PlayerAnalysis.puuid)
            .where(
                PlayerORM.is_tracked == False,  # noqa: E712
                PlayerORM.is_active == True,  # noqa: E712
                PlayerAnalysis.puuid.is_(None),  # No analysis exists
            )
            .group_by(PlayerORM.puuid)
            .having(func.count(MatchParticipant.match_id) >= min_matches)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        players = list(result.scalars().all())

        logger.debug(
            "players_ready_for_analysis_retrieved",
            count=len(players),
            min_matches=min_matches,
        )

        return players

    async def get_players_for_ban_check(
        self, cutoff: datetime, limit: int
    ) -> list[PlayerORM]:
        """Get detected smurfs needing ban status check.

        Join query with PlayerAnalysis to find players marked as smurfs
        who need their ban status checked.
        """
        from app.features.player_analysis.orm_models import (
            PlayerAnalysisORM as PlayerAnalysis,
        )

        stmt = (
            select(PlayerORM)
            .options(selectinload(PlayerORM.ranks))
            .join(PlayerAnalysis, PlayerORM.puuid == PlayerAnalysis.puuid)
            .where(
                PlayerAnalysis.is_smurf == True,  # noqa: E712
                or_(
                    PlayerORM.last_ban_check.is_(None),
                    PlayerORM.last_ban_check < cutoff,
                ),
            )
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        players = list(result.scalars().all())

        logger.debug(
            "players_for_ban_check_retrieved",
            count=len(players),
            cutoff=cutoff,
        )

        return players

    async def create_rank(self, rank: "PlayerRankORM") -> "PlayerRankORM":
        """Create new rank record for a player."""
        self.db.add(rank)
        await self.db.commit()
        await self.db.refresh(rank)

        logger.info(
            "rank_created",
            puuid=rank.puuid,
            queue_type=rank.queue_type,
            tier=rank.tier,
        )

        return rank

    async def get_rank_by_puuid(
        self, puuid: str, queue_type: str
    ) -> Optional["PlayerRankORM"]:
        """Get most recent rank for a player by queue type."""
        stmt = (
            select(PlayerRankORM)
            .where(
                PlayerRankORM.puuid == puuid,
                PlayerRankORM.queue_type == queue_type,
            )
            .order_by(PlayerRankORM.updated_at.desc())
            .limit(1)
        )

        result = await self.db.execute(stmt)
        rank = result.scalar_one_or_none()

        if rank:
            logger.debug(
                "rank_retrieved",
                puuid=puuid,
                queue_type=queue_type,
                tier=rank.tier,
            )

        return rank
