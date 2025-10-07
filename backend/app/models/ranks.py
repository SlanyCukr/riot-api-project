"""
Player rank model for storing ranked information.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import Base


class Tier(str, Enum):
    """League of Legends rank tiers."""
    IRON = "IRON"
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"
    EMERALD = "EMERALD"
    DIAMOND = "DIAMOND"
    MASTER = "MASTER"
    GRANDMASTER = "GRANDMASTER"
    CHALLENGER = "CHALLENGER"


class Division(str, Enum):
    """League of Legends rank divisions."""
    I = "I"
    II = "II"
    III = "III"
    IV = "IV"


class QueueType(str, Enum):
    """League of Legends queue types."""
    RANKED_SOLO_5x5 = "RANKED_SOLO_5x5"
    RANKED_FLEX_5x5 = "RANKED_FLEX_SR"
    RANKED_FLEX_3x3 = "RANKED_FLEX_TT"


class PlayerRank(Base):
    """Player rank model storing ranked information."""

    __tablename__ = "player_ranks"

    # Primary key
    id = Column(
        Integer,
        primary_key=True,
        comment="Auto-incrementing primary key"
    )

    # Foreign key
    puuid = Column(
        String(78),
        ForeignKey("players.puuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the player"
    )

    # Queue and rank information
    queue_type = Column(
        String(32),
        nullable=False,
        index=True,
        comment="Queue type (e.g., RANKED_SOLO_5x5, RANKED_FLEX_SR)"
    )

    tier = Column(
        String(16),
        nullable=False,
        index=True,
        comment="Rank tier (e.g., GOLD, PLATINUM, DIAMOND)"
    )

    rank = Column(
        String(4),
        nullable=True,
        index=True,
        comment="Rank division (I, II, III, IV)"
    )

    league_points = Column(
        Integer,
        nullable=False,
        default=0,
        comment="League points (0-100)"
    )

    wins = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of wins in this queue"
    )

    losses = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of losses in this queue"
    )

    veteran = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the player is a veteran"
    )

    inactive = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the player is inactive"
    )

    fresh_blood = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the player is fresh blood"
    )

    hot_streak = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the player is on a hot streak"
    )

    # League information
    league_id = Column(
        String(64),
        nullable=True,
        index=True,
        comment="League ID"
    )

    league_name = Column(
        String(64),
        nullable=True,
        comment="League name"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this rank record was created"
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="When this rank record was last updated"
    )

    # Season information
    season_id = Column(
        String(16),
        nullable=True,
        index=True,
        comment="Season identifier"
    )

    # Is current rank flag
    is_current = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this is the current rank for the player"
    )

    # Relationships
    player = relationship("Player", back_populates="ranks")

    def __repr__(self) -> str:
        """String representation of the player rank."""
        return f"<PlayerRank(puuid='{self.puuid}', queue='{self.queue_type}', tier='{self.tier}', rank='{self.rank}')>"

    def to_dict(self) -> dict:
        """Convert player rank to dictionary representation."""
        return {
            "id": self.id,
            "puuid": str(self.puuid),
            "queue_type": self.queue_type,
            "tier": self.tier,
            "rank": self.rank,
            "league_points": self.league_points,
            "wins": self.wins,
            "losses": self.losses,
            "veteran": self.veteran,
            "inactive": self.inactive,
            "fresh_blood": self.fresh_blood,
            "hot_streak": self.hot_streak,
            "league_id": self.league_id,
            "league_name": self.league_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "season_id": self.season_id,
            "is_current": self.is_current,
        }

    @property
    def win_rate(self) -> float:
        """Calculate win rate as a percentage."""
        total_games = self.wins + self.losses
        if total_games == 0:
            return 0.0
        return (self.wins / total_games) * 100

    @property
    def total_games(self) -> int:
        """Get total number of games played."""
        return self.wins + self.losses

    @property
    def display_rank(self) -> str:
        """Get the display rank (e.g., 'Gold II')."""
        if self.rank:
            return f"{self.tier.title()} {self.rank}"
        return self.tier.title()

    @property
    def display_lp(self) -> str:
        """Get the display LP (e.g., '75 LP')."""
        if self.tier in ["MASTER", "GRANDMASTER", "CHALLENGER"]:
            return f"{self.league_points} LP"
        return f"{self.league_points} LP"

    def is_high_tier(self) -> bool:
        """Check if this is a high tier rank."""
        return self.tier in ["MASTER", "GRANDMASTER", "CHALLENGER"]

    def is_diamond_plus(self) -> bool:
        """Check if this is diamond or above."""
        return self.tier in ["DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]

    def is_platinum_plus(self) -> bool:
        """Check if this is platinum or above."""
        return self.tier in ["PLATINUM", "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]


# Create composite indexes for common queries
Index(
    "idx_ranks_puuid_queue",
    PlayerRank.puuid,
    PlayerRank.queue_type
)

Index(
    "idx_ranks_tier_rank",
    PlayerRank.tier,
    PlayerRank.rank
)

Index(
    "idx_ranks_queue_current",
    PlayerRank.queue_type,
    PlayerRank.is_current
)

Index(
    "idx_ranks_puuid_current",
    PlayerRank.puuid,
    PlayerRank.is_current
)

Index(
    "idx_ranks_tier_lp",
    PlayerRank.tier,
    PlayerRank.league_points
)