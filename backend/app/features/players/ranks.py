"""Player rank model for storing ranked information."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime as SQLDateTime,
    ForeignKey,
    Integer,
    String,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.models import Base


class PlayerRank(Base):
    """Player rank model storing ranked information."""

    __tablename__ = "player_ranks"
    __table_args__ = {"schema": "core", "extend_existing": True}

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="Auto-incrementing primary key"
    )

    # Foreign key
    puuid: Mapped[str] = mapped_column(
        String(78),
        ForeignKey("core.players.puuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the player (Riot PUUID)",
    )

    # Queue and rank information
    queue_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="Queue type (e.g., RANKED_SOLO_5x5, RANKED_FLEX_SR)",
    )

    tier: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        index=True,
        comment="Rank tier (e.g., GOLD, PLATINUM, DIAMOND)",
    )

    rank: Mapped[Optional[str]] = mapped_column(
        String(4), nullable=True, index=True, comment="Rank division (I, II, III, IV)"
    )

    league_points: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="League points (0-100)"
    )

    wins: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Number of wins in this queue"
    )

    losses: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Number of losses in this queue"
    )

    veteran: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the player is a veteran",
    )

    inactive: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="Whether the player is inactive"
    )

    fresh_blood: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the player is fresh blood",
    )

    hot_streak: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the player is on a hot streak",
    )

    # League information
    league_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True, comment="League ID"
    )

    league_name: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="League name"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this rank record was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="When this rank record was last updated",
    )

    # Season information
    season_id: Mapped[Optional[str]] = mapped_column(
        String(16), nullable=True, index=True, comment="Season identifier"
    )

    # Is current rank flag
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this is the current rank for the player",
    )

    # Relationships - Note: This model is deprecated, use PlayerRankORM from orm_models.py
    # player = relationship("PlayerORM", back_populates="ranks")

    def __repr__(self) -> str:
        """Return string representation of the player rank."""
        return f"<PlayerRank(puuid='{self.puuid}', queue='{self.queue_type}', tier='{self.tier}', rank='{self.rank}')>"

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


# Create composite indexes for common queries
Index("idx_ranks_puuid_queue", PlayerRank.puuid, PlayerRank.queue_type)

Index("idx_ranks_tier_rank", PlayerRank.tier, PlayerRank.rank)

Index("idx_ranks_queue_current", PlayerRank.queue_type, PlayerRank.is_current)

Index("idx_ranks_puuid_current", PlayerRank.puuid, PlayerRank.is_current)

Index("idx_ranks_tier_lp", PlayerRank.tier, PlayerRank.league_points)
