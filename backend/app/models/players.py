"""Player data model for storing player information."""

from typing import Any, Dict, Optional
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

from . import Base


class Player(Base):
    """Player model storing Riot API player data."""

    __tablename__ = "players"

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
        String(8), nullable=True, comment="Player's tag line (region identifier)"
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

    # Relationships
    match_participations = relationship(
        "MatchParticipant", back_populates="player", cascade="all, delete-orphan"
    )
    ranks = relationship(
        "PlayerRank", back_populates="player", cascade="all, delete-orphan"
    )
    smurf_detections = relationship(
        "SmurfDetection", back_populates="player", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """Return string representation of the player."""
        return f"<Player(puuid='{self.puuid}', summoner_name='{self.summoner_name}', platform='{self.platform}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert player to dictionary representation."""
        return {
            "puuid": str(self.puuid),
            "riot_id": self.riot_id,
            "tag_line": self.tag_line,
            "summoner_name": self.summoner_name,
            "platform": self.platform,
            "account_level": self.account_level,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "is_active": self.is_active,
            "profile_icon_id": self.profile_icon_id,
            "summoner_id": self.summoner_id,
        }

    @property
    def full_riot_id(self) -> Optional[str]:
        """Get the full Riot ID (gameName#tagLine)."""
        if self.riot_id and self.tag_line:
            return f"{self.riot_id}#{self.tag_line}"
        return None


# Create composite indexes for common queries
Index("idx_players_summoner_platform", Player.summoner_name, Player.platform)

Index("idx_players_riot_tag", Player.riot_id, Player.tag_line)

Index("idx_players_last_seen_active", Player.last_seen, Player.is_active)
