"""Match data model for storing League of Legends match information."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Integer,
    String,
    Boolean,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import Base


class Match(Base):
    """Match model storing League of Legends match data."""

    __tablename__ = "matches"

    # Primary key - match ID from Riot API
    match_id = Column(
        String(64),
        primary_key=True,
        index=True,
        comment="Unique match identifier from Riot API",
    )

    # Platform and routing information
    platform_id = Column(
        String(8),
        nullable=False,
        index=True,
        comment="Platform where the match was played (e.g., EUW1, EUN1)",
    )

    # Game information
    game_creation = Column(
        BigInteger,
        nullable=False,
        index=True,
        comment="Game creation timestamp in milliseconds since epoch",
    )

    game_duration = Column(Integer, nullable=False, comment="Game duration in seconds")

    queue_id = Column(
        Integer,
        nullable=False,
        index=True,
        comment="Queue type ID (e.g., 420=Ranked Solo, 440=Ranked Flex)",
    )

    game_version = Column(
        String(32),
        nullable=False,
        index=True,
        comment="Game version (e.g., '14.20.555.5555')",
    )

    map_id = Column(
        Integer, nullable=False, comment="Map ID (e.g., 11=Summoner's Rift)"
    )

    # Game mode information
    game_mode = Column(
        String(32),
        nullable=True,
        index=True,
        comment="Game mode (e.g., 'CLASSIC', 'ARAM')",
    )

    game_type = Column(
        String(32),
        nullable=True,
        index=True,
        comment="Game type (e.g., 'MATCHED_GAME')",
    )

    # Match result
    game_end_timestamp = Column(
        BigInteger,
        nullable=True,
        comment="Game end timestamp in milliseconds since epoch",
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this match record was created in our database",
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="When this match record was last updated",
    )

    # Additional match metadata
    tournament_id = Column(
        String(64),
        nullable=True,
        index=True,
        comment="Tournament ID if this is a tournament match",
    )

    # Processing flags
    is_processed = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether this match has been processed for smurf detection",
    )

    processing_error = Column(
        String(256), nullable=True, comment="Error message if match processing failed"
    )

    # Relationships
    participants = relationship(
        "MatchParticipant", back_populates="match", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """Return string representation of the match."""
        return f"<Match(match_id='{self.match_id}', queue_id={self.queue_id}, game_creation={self.game_creation})>"

    def to_dict(self) -> dict:
        """Convert match to dictionary representation."""
        return {
            "match_id": self.match_id,
            "platform_id": self.platform_id,
            "game_creation": self.game_creation,
            "game_duration": self.game_duration,
            "queue_id": self.queue_id,
            "game_version": self.game_version,
            "map_id": self.map_id,
            "game_mode": self.game_mode,
            "game_type": self.game_type,
            "game_end_timestamp": self.game_end_timestamp,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "tournament_id": self.tournament_id,
            "is_processed": self.is_processed,
            "processing_error": self.processing_error,
        }

    @property
    def game_start_datetime(self) -> Optional[datetime]:
        """Get game creation as a datetime object."""
        if self.game_creation:
            return datetime.fromtimestamp(self.game_creation / 1000)
        return None

    @property
    def game_end_datetime(self) -> Optional[datetime]:
        """Get game end as a datetime object."""
        if self.game_end_timestamp:
            return datetime.fromtimestamp(self.game_end_timestamp / 1000)
        elif self.game_creation and self.game_duration:
            return datetime.fromtimestamp(
                (self.game_creation + self.game_duration * 1000) / 1000
            )
        return None

    @property
    def patch_version(self) -> Optional[str]:
        """Extract patch version from game version."""
        if self.game_version:
            # Game version format: "14.20.555.5555" -> extract "14.20"
            version_parts = self.game_version.split(".")
            if len(version_parts) >= 2:
                return f"{version_parts[0]}.{version_parts[1]}"
        return None

    def is_ranked_match(self) -> bool:
        """Check if this is a ranked match."""
        return self.queue_id in [420, 440]  # Ranked Solo/Duo and Ranked Flex

    def is_normal_match(self) -> bool:
        """Check if this is a normal match."""
        return self.queue_id in [400, 430]  # Normal Draft and Blind Pick


# Create indexes for common queries
Index("idx_matches_platform_creation", Match.platform_id, Match.game_creation)

Index("idx_matches_queue_creation", Match.queue_id, Match.game_creation)

Index("idx_matches_version_creation", Match.game_version, Match.game_creation)

Index("idx_matches_processed_error", Match.is_processed, Match.processing_error)
