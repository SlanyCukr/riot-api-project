"""Player data model for storing player information."""

from typing import Optional
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime as SQLDateTime,
    Integer,
    String,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import sqlalchemy as sa

from app.core.models import Base


class Player(Base):
    """Player model storing Riot API player data."""

    __tablename__ = "players"
    __table_args__ = {"schema": "core"}

    # Primary key - PUUID is the unique identifier from Riot API
    # Note: Riot PUUID is a base64-encoded string, not a standard UUID
    puuid: Mapped[str] = mapped_column(
        String(78),  # Riot PUUIDs are 78 characters
        primary_key=True,
        index=True,
        comment="Player's universally unique identifier from Riot API",
    )

    # Riot ID information
    riot_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, index=True, comment="Player's Riot ID (game name)"
    )

    tag_line: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, comment="Player's tag line (region identifier)"
    )

    # Summoner information (may change over time)
    summoner_name: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        index=True,
        comment="Current summoner name (can change)",
    )

    platform: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        index=True,
        comment="Platform where the player was last seen (e.g., EUW1, EUN1)",
    )

    # Player statistics
    account_level: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Player's account level"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this player record was first created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="When this player record was last updated",
    )

    last_seen: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="When this player was last seen in a match",
    )

    # Soft deletion flag
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this player record is active (not deleted)",
    )

    # Tracking flags for automated jobs
    is_tracked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether this player is being actively tracked for continuous updates",
    )

    is_analyzed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether this player has been analyzed for smurf/boosted detection",
    )

    matches_exhausted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
        index=True,
        comment="True when all available matches have been fetched from Riot API",
    )

    last_ban_check: Mapped[Optional[datetime]] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When this player was last checked for ban status",
    )

    # Additional metadata fields
    profile_icon_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Profile icon ID"
    )

    summoner_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Encrypted summoner ID (used for some Riot API endpoints)",
    )

    def __repr__(self) -> str:
        """Return string representation of the player."""
        return f"<Player(puuid='{self.puuid}', summoner_name='{self.summoner_name}', platform='{self.platform}')>"

    # Database-only relationships - used by SQLAlchemy ORM but not directly referenced in Python code
    # These relationships enable database queries and cascade operations
    match_participations = relationship(  # noqa: F841 - Used by SQLAlchemy ORM
        "MatchParticipant", back_populates="player", cascade="all, delete-orphan"
    )
    player_analysis = relationship(  # noqa: F841 - Used by SQLAlchemy ORM
        "PlayerAnalysis", back_populates="player", cascade="all, delete-orphan"
    )
    ranks = relationship(  # noqa: F841 - Used by SQLAlchemy ORM
        "PlayerRank", back_populates="player", cascade="all, delete-orphan"
    )


# Create composite indexes for common queries
Index("idx_players_summoner_platform", Player.summoner_name, Player.platform)

Index("idx_players_riot_tag", Player.riot_id, Player.tag_line)

Index("idx_players_last_seen_active", Player.last_seen, Player.is_active)
