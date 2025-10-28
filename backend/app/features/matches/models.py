"""Match data model for storing League of Legends match information."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Column, DateTime as SQLDateTime, Index
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel


class MatchBase(SQLModel):
    """Base match schema with shared fields."""

    # Platform and routing information
    platform_id: str = Field(
        max_length=8,
        index=True,
        description="Platform where the match was played (e.g., EUW1, EUN1)",
    )

    # Game information
    game_creation: int = Field(
        description="Game creation timestamp in milliseconds since epoch",
        sa_column=Column(BigInteger, nullable=False, index=True),
    )

    game_duration: int = Field(description="Game duration in seconds")

    queue_id: int = Field(
        index=True,
        description="Queue type ID (e.g., 420=Ranked Solo, 440=Ranked Flex)",
    )

    game_version: str = Field(
        max_length=32,
        index=True,
        description="Game version (e.g., '14.20.555.5555')",
    )

    map_id: int = Field(description="Map ID (e.g., 11=Summoner's Rift)")

    # Game mode information
    game_mode: Optional[str] = Field(
        default=None,
        max_length=32,
        index=True,
        description="Game mode (e.g., 'CLASSIC', 'ARAM')",
    )

    game_type: Optional[str] = Field(
        default=None,
        max_length=32,
        index=True,
        description="Game type (e.g., 'MATCHED_GAME')",
    )

    # Match result
    game_end_timestamp: Optional[int] = Field(
        default=None,
        description="Game end timestamp in milliseconds since epoch",
        sa_column=Column(BigInteger, nullable=True),
    )

    # Additional match metadata
    tournament_id: Optional[str] = Field(
        default=None,
        max_length=64,
        index=True,
        description="Tournament ID if this is a tournament match",
    )

    # Processing flags
    is_processed: bool = Field(
        default=False,
        index=True,
        description="Whether this match has been processed for player analysis",
    )

    processing_error: Optional[str] = Field(
        default=None,
        max_length=256,
        description="Error message if match processing failed",
    )


class Match(MatchBase, table=True):
    """Match model storing League of Legends match data."""

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

    # Primary key - match ID from Riot API (string, not auto-increment)
    match_id: str = Field(
        primary_key=True,
        max_length=64,
        index=True,
        description="Unique match identifier from Riot API",
    )

    # Timestamps - let PostgreSQL handle defaults
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            SQLDateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
        description="When this match record was created in our database",
    )

    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            SQLDateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
        description="When this match record was last updated",
    )

    # Relationships
    participants: list["MatchParticipant"] = Relationship(
        back_populates="match",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    def __repr__(self) -> str:
        """Return string representation of the match."""
        return f"<Match(match_id='{self.match_id}', queue_id={self.queue_id}, game_creation={self.game_creation})>"
