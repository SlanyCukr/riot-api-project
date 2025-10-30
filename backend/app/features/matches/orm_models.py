"""SQLAlchemy 2.0 ORM models for matches feature with Rich Domain Model pattern.

This module defines database models following Martin Fowler's Rich Domain Model pattern,
where business logic and behavior are combined with data in domain objects.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime as SQLDateTime,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.models import Base

if TYPE_CHECKING:
    from app.features.matches.participants_orm import MatchParticipantORM


class MatchORM(Base):
    """Match domain model (Rich Domain Model pattern).

    Combines data and behavior:
    - Database fields with type safety (SQLAlchemy 2.0 Mapped types)
    - Business logic methods (game type detection, duration calculations, etc.)
    - Domain calculations and rules
    """

    __tablename__ = "matches"
    __table_args__ = (
        Index("idx_matches_platform_creation", "platform_id", "game_creation"),
        Index("idx_matches_queue_creation", "queue_id", "game_creation"),
        Index("idx_matches_version_creation", "game_version", "game_creation"),
        Index("idx_matches_processed_error", "is_processed", "processing_error"),
        Index("idx_matches_creation_queue", "game_creation", "queue_id"),
        Index("idx_matches_processed_creation", "is_processed", "game_creation"),
        {"schema": "core"},
    )

    # ========================================================================
    # DATABASE FIELDS
    # ========================================================================

    # Primary key - match ID from Riot API
    match_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        index=True,
        comment="Unique match identifier from Riot API",
    )

    # Platform and routing information
    platform_id: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        index=True,
        comment="Platform where the match was played (e.g., EUW1, EUN1)",
    )

    # Game information
    game_creation: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
        comment="Game creation timestamp in milliseconds since epoch",
    )

    game_duration: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Game duration in seconds",
    )

    queue_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Queue type ID (e.g., 420=Ranked Solo, 440=Ranked Flex)",
    )

    game_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="Game version (e.g., '14.20.555.5555')",
    )

    map_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Map ID (e.g., 11=Summoner's Rift)",
    )

    # Game mode information
    game_mode: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        index=True,
        comment="Game mode (e.g., 'CLASSIC', 'ARAM')",
    )

    game_type: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        index=True,
        comment="Game type (e.g., 'MATCHED_GAME')",
    )

    # Match result
    game_end_timestamp: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Game end timestamp in milliseconds since epoch",
    )

    # Additional match metadata
    tournament_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Tournament ID if this is a tournament match",
    )

    # Processing flags
    is_processed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether this match has been processed for player analysis",
    )

    processing_error: Mapped[Optional[str]] = mapped_column(
        String(256),
        nullable=True,
        comment="Error message if match processing failed",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this match record was created in our database",
    )

    updated_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="When this match record was last updated",
    )

    # ========================================================================
    # RELATIONSHIPS
    # ========================================================================

    # Type-safe relationships with Mapped
    participants: Mapped[list["MatchParticipantORM"]] = relationship(
        "MatchParticipantORM",
        back_populates="match",
        cascade="all, delete-orphan",
        lazy="selectin",  # Eager loading for common access pattern
    )

    # ========================================================================
    # RICH DOMAIN MODEL - Business Logic Methods
    # ========================================================================

    def is_ranked_game(self) -> bool:
        """Determine if this is a ranked game.

        Business rule: Queue IDs 420 (Ranked Solo/Duo) and 440 (Ranked Flex)
        are considered ranked games.

        :returns: True if ranked game
        """
        return self.queue_id in (420, 440)

    def get_duration_minutes(self) -> float:
        """Get game duration in minutes.

        Business calculation converting seconds to minutes.

        :returns: Game duration in minutes with decimal precision
        """
        return self.game_duration / 60.0

    def is_recent(self, days: int = 7) -> bool:
        """Check if match is recent.

        Business rule for determining match recency based on game_creation timestamp.

        :param days: Number of days to consider as recent
        :returns: True if match was created within the specified days
        """
        # Convert game_creation from milliseconds to datetime
        game_datetime = datetime.fromtimestamp(
            self.game_creation / 1000, tz=timezone.utc
        )
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        return game_datetime >= cutoff_date

    def get_winning_team_id(self) -> int | None:
        """Determine the winning team ID.

        Business logic to identify the winning team by checking participant results.

        :returns: Team ID (100 or 200) that won, or None if no participants or data incomplete
        """
        if not self.participants:
            return None

        # Find a winning participant and return their team ID
        for participant in self.participants:
            if participant.win:
                return participant.team_id

        return None

    def is_valid_game(self) -> bool:
        """Determine if this is a valid complete game.

        Business rule: Game must be at least 5 minutes long to be considered valid
        (excludes remakes and early surrenders for analysis).

        :returns: True if game duration is >= 5 minutes
        """
        return self.get_duration_minutes() >= 5.0

    def is_summoners_rift(self) -> bool:
        """Check if this match was played on Summoner's Rift.

        Business rule: Map ID 11 is Summoner's Rift.

        :returns: True if played on Summoner's Rift
        """
        return self.map_id == 11

    def get_game_creation_datetime(self) -> datetime:
        """Get game creation time as datetime object.

        Utility method to convert millisecond timestamp to datetime.

        :returns: Game creation time as timezone-aware datetime
        """
        return datetime.fromtimestamp(self.game_creation / 1000, tz=timezone.utc)

    def get_patch_version(self) -> str:
        """Extract patch version from game version.

        Business formatting: Extract major.minor patch (e.g., "14.20" from "14.20.555.5555").

        :returns: Patch version string (e.g., "14.20")
        """
        parts = self.game_version.split(".")
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"
        return self.game_version

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<MatchORM(match_id='{self.match_id}', "
            f"queue_id={self.queue_id}, "
            f"duration={self.get_duration_minutes():.1f}m, "
            f"ranked={self.is_ranked_game()})>"
        )
