"""Repository pattern implementation for matches feature.

This module provides data access abstraction following Martin Fowler's Repository pattern,
encapsulating all database operations and providing a collection-like interface.
"""

from abc import ABC, abstractmethod
from typing import Optional

import structlog
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .orm_models import MatchORM
from .participants_orm import MatchParticipantORM

logger = structlog.get_logger(__name__)


class MatchRepositoryInterface(ABC):
    """Interface for match repository following Repository pattern.

    Provides collection-like semantics for accessing match domain objects.
    """

    @abstractmethod
    async def get_by_id(self, match_id: str) -> Optional[MatchORM]:
        """Get match by ID with eager-loaded participants.

        Args:
            match_id: Match identifier

        Returns:
            MatchORM if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_player(
        self,
        puuid: str,
        limit: int = 20,
        offset: int = 0,
        queue_id: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> list[MatchORM]:
        """Find matches for a player with filtering.

        Args:
            puuid: Player PUUID
            limit: Maximum number of matches to return
            offset: Offset for pagination
            queue_id: Optional queue filter
            start_time: Optional start timestamp filter (milliseconds)
            end_time: Optional end timestamp filter (milliseconds)

        Returns:
            List of MatchORM objects with participants eager-loaded
        """
        pass

    @abstractmethod
    async def count_player_matches(
        self,
        puuid: str,
        queue_id: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> int:
        """Count total matches for a player.

        Args:
            puuid: Player PUUID
            queue_id: Optional queue filter
            start_time: Optional start timestamp filter
            end_time: Optional end timestamp filter

        Returns:
            Total match count
        """
        pass

    @abstractmethod
    async def get_player_last_match_time(self, puuid: str) -> Optional[int]:
        """Get timestamp of player's most recent match.

        Args:
            puuid: Player PUUID

        Returns:
            Timestamp in milliseconds, or None if no matches
        """
        pass

    @abstractmethod
    async def filter_existing_matches(self, match_ids: list[str]) -> list[str]:
        """Filter out matches that already exist in database.

        Args:
            match_ids: List of match IDs to check

        Returns:
            List of match IDs NOT in database (new matches)
        """
        pass

    @abstractmethod
    async def create(self, match: MatchORM) -> MatchORM:
        """Add new match to database.

        Args:
            match: Match domain object to persist

        Returns:
            Persisted match with updated fields
        """
        pass

    @abstractmethod
    async def save(self, match: MatchORM) -> MatchORM:
        """Save existing match changes.

        Args:
            match: Match domain object with changes

        Returns:
            Saved match with updated timestamps
        """
        pass

    @abstractmethod
    async def mark_as_processed(self, match_ids: list[str]) -> None:
        """Mark matches as processed for analysis.

        Args:
            match_ids: List of match IDs to mark
        """
        pass


class SQLAlchemyMatchRepository(MatchRepositoryInterface):
    """SQLAlchemy implementation of match repository.

    Encapsulates all database access logic for matches using SQLAlchemy 2.0.
    """

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session.

        Args:
            db: SQLAlchemy async session
        """
        self.db = db

    async def get_by_id(self, match_id: str) -> Optional[MatchORM]:
        """Get match by ID with eager-loaded participants."""
        stmt = (
            select(MatchORM)
            .options(selectinload(MatchORM.participants))
            .where(MatchORM.match_id == match_id)
        )

        result = await self.db.execute(stmt)
        match = result.scalar_one_or_none()

        if match:
            logger.debug("match_retrieved", match_id=match_id)

        return match

    async def find_by_player(
        self,
        puuid: str,
        limit: int = 20,
        offset: int = 0,
        queue_id: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> list[MatchORM]:
        """Find matches for a player with filtering."""
        # Build query with participant join
        stmt = (
            select(MatchORM)
            .join(MatchParticipantORM)
            .where(MatchParticipantORM.puuid == puuid)
            .order_by(desc(MatchORM.game_creation))
            .offset(offset)
            .limit(limit)
        )

        # Apply optional filters
        if queue_id:
            stmt = stmt.where(MatchORM.queue_id == queue_id)
        if start_time:
            stmt = stmt.where(MatchORM.game_creation >= start_time)
        if end_time:
            stmt = stmt.where(MatchORM.game_creation <= end_time)

        # Eager load participants to avoid N+1
        stmt = stmt.options(selectinload(MatchORM.participants))

        result = await self.db.execute(stmt)
        matches = list(result.scalars().all())

        logger.debug(
            "matches_found_for_player",
            puuid=puuid,
            count=len(matches),
            queue_id=queue_id,
        )

        return matches

    async def count_player_matches(
        self,
        puuid: str,
        queue_id: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> int:
        """Count total matches for a player."""
        stmt = (
            select(func.count(MatchORM.match_id))
            .join(MatchParticipantORM)
            .where(MatchParticipantORM.puuid == puuid)
        )

        # Apply optional filters
        if queue_id:
            stmt = stmt.where(MatchORM.queue_id == queue_id)
        if start_time:
            stmt = stmt.where(MatchORM.game_creation >= start_time)
        if end_time:
            stmt = stmt.where(MatchORM.game_creation <= end_time)

        result = await self.db.execute(stmt)
        count = result.scalar_one()

        logger.debug("player_match_count", puuid=puuid, count=count)

        return count

    async def get_player_last_match_time(self, puuid: str) -> Optional[int]:
        """Get timestamp of player's most recent match."""
        stmt = (
            select(MatchORM.game_creation)
            .join(MatchParticipantORM)
            .where(MatchParticipantORM.puuid == puuid)
            .order_by(desc(MatchORM.game_creation))
            .limit(1)
        )

        result = await self.db.execute(stmt)
        timestamp = result.scalar_one_or_none()

        if timestamp:
            logger.debug("last_match_time_retrieved", puuid=puuid, timestamp=timestamp)

        return timestamp

    async def filter_existing_matches(self, match_ids: list[str]) -> list[str]:
        """Filter out matches that already exist in database."""
        if not match_ids:
            return []

        stmt = select(MatchORM.match_id).where(MatchORM.match_id.in_(match_ids))
        result = await self.db.execute(stmt)
        existing_match_ids = set(result.scalars().all())

        new_match_ids = [mid for mid in match_ids if mid not in existing_match_ids]

        logger.debug(
            "filtered_existing_matches",
            total=len(match_ids),
            existing=len(existing_match_ids),
            new=len(new_match_ids),
        )

        return new_match_ids

    async def create(self, match: MatchORM) -> MatchORM:
        """Add new match to database."""
        self.db.add(match)
        await self.db.commit()
        await self.db.refresh(match)

        logger.info("match_created", match_id=match.match_id)

        return match

    async def save(self, match: MatchORM) -> MatchORM:
        """Save existing match changes."""
        await self.db.commit()
        await self.db.refresh(match)

        logger.debug("match_saved", match_id=match.match_id)

        return match

    async def mark_as_processed(self, match_ids: list[str]) -> None:
        """Mark matches as processed for analysis."""
        if not match_ids:
            return

        # Bulk update
        stmt = select(MatchORM).where(MatchORM.match_id.in_(match_ids))
        result = await self.db.execute(stmt)
        matches = result.scalars().all()

        for match in matches:
            match.is_processed = True

        await self.db.commit()

        logger.debug("matches_marked_processed", count=len(match_ids))


class MatchParticipantRepositoryInterface(ABC):
    """Interface for match participant repository."""

    @abstractmethod
    async def get_by_match_and_player(
        self, match_id: str, puuid: str
    ) -> Optional[MatchParticipantORM]:
        """Get participant by match and player.

        Args:
            match_id: Match identifier
            puuid: Player PUUID

        Returns:
            MatchParticipantORM if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_match(self, match_id: str) -> list[MatchParticipantORM]:
        """Find all participants in a match.

        Args:
            match_id: Match identifier

        Returns:
            List of participants
        """
        pass

    @abstractmethod
    async def create_bulk(self, participants: list[MatchParticipantORM]) -> None:
        """Add multiple participants at once.

        Args:
            participants: List of participant objects to persist
        """
        pass


class SQLAlchemyMatchParticipantRepository(MatchParticipantRepositoryInterface):
    """SQLAlchemy implementation of match participant repository."""

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session."""
        self.db = db

    async def get_by_match_and_player(
        self, match_id: str, puuid: str
    ) -> Optional[MatchParticipantORM]:
        """Get participant by match and player."""
        stmt = select(MatchParticipantORM).where(
            and_(
                MatchParticipantORM.match_id == match_id,
                MatchParticipantORM.puuid == puuid,
            )
        )

        result = await self.db.execute(stmt)
        participant = result.scalar_one_or_none()

        if participant:
            logger.debug(
                "participant_retrieved",
                match_id=match_id,
                puuid=puuid,
            )

        return participant

    async def find_by_match(self, match_id: str) -> list[MatchParticipantORM]:
        """Find all participants in a match."""
        stmt = select(MatchParticipantORM).where(
            MatchParticipantORM.match_id == match_id
        )

        result = await self.db.execute(stmt)
        participants = list(result.scalars().all())

        logger.debug(
            "participants_found_for_match",
            match_id=match_id,
            count=len(participants),
        )

        return participants

    async def create_bulk(self, participants: list[MatchParticipantORM]) -> None:
        """Add multiple participants at once."""
        self.db.add_all(participants)
        await self.db.commit()

        logger.debug("participants_created_bulk", count=len(participants))
