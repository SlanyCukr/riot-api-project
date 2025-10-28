"""SQLAlchemy 2.0 ORM models for players feature with Rich Domain Model pattern.

This module defines database models following Martin Fowler's Rich Domain Model pattern,
where business logic and behavior are combined with data in domain objects.
"""

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime as SQLDateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.models import Base

if TYPE_CHECKING:
    from app.features.matches.participants import MatchParticipant
    from app.features.player_analysis.models import PlayerAnalysis


class PlayerORM(Base):
    """Player domain model (Rich Domain Model pattern).

    Combines data and behavior:
    - Database fields with type safety (SQLAlchemy 2.0 Mapped types)
    - Business logic methods (smurf detection, validation, etc.)
    - Domain calculations and rules
    """

    __tablename__ = "players"
    __table_args__ = (
        Index("idx_players_summoner_platform", "summoner_name", "platform"),
        Index("idx_players_riot_tag", "riot_id", "tag_line"),
        Index("idx_players_last_seen_active", "last_seen", "is_active"),
        {"schema": "core"},
    )

    # ========================================================================
    # DATABASE FIELDS
    # ========================================================================

    # Primary key - PUUID is the unique identifier from Riot API
    puuid: Mapped[str] = mapped_column(
        String(78),
        primary_key=True,
        index=True,
        comment="Player's universally unique identifier from Riot API",
    )

    # Riot ID information
    riot_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="Player's Riot ID (game name)",
    )

    tag_line: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="Player's tag line (region identifier)",
    )

    # Platform
    platform: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        index=True,
        comment="Platform where the player was last seen (e.g., EUW1, EUN1)",
    )

    # Summoner information (may change over time)
    summoner_name: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        index=True,
        comment="Current summoner name (can change)",
    )

    summoner_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Encrypted summoner ID (used for some Riot API endpoints)",
    )

    # Player statistics
    account_level: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Player's account level",
    )

    profile_icon_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Profile icon ID",
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

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this player record is active (not soft-deleted)",
    )

    matches_exhausted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="True when all available matches have been fetched from Riot API",
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

    last_ban_check: Mapped[Optional[datetime]] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When this player was last checked for ban status",
    )

    # ========================================================================
    # RELATIONSHIPS
    # ========================================================================

    # Type-safe relationships with Mapped
    ranks: Mapped[list["PlayerRankORM"]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
    )

    match_participations: Mapped[list["MatchParticipant"]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
    )

    player_analyses: Mapped[list["PlayerAnalysis"]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
    )

    # ========================================================================
    # RICH DOMAIN MODEL - Business Logic Methods
    # ========================================================================

    def is_new_account(self) -> bool:
        """Determine if player has a new account.

        Business rule: Accounts below level 30 are considered new.
        Used for smurf detection algorithms.

        :returns: True if account level is below 30
        """
        return self.account_level is not None and self.account_level < 30

    def is_veteran(self) -> bool:
        """Determine if player is a veteran.

        Business rule: Level 100+ with 500+ total games across ranked queues.

        :returns: True if player meets veteran criteria
        """
        if not self.account_level or self.account_level < 100:
            return False

        # Check if they have rank data with sufficient games
        if self.ranks:
            total_games = sum(r.total_games for r in self.ranks if r.is_current)
            return total_games >= 500

        return False

    def calculate_smurf_likelihood(self) -> float:
        """Calculate likelihood that this player is a smurf account.

        Business logic combining multiple factors:
        - New account (low level)
        - High win rate
        - High rank for account level

        :returns: Score between 0.0 and 1.0 (0 = unlikely, 1 = very likely)
        """
        score = 0.0
        score += self._get_new_account_score()
        score += self._get_win_rate_score()
        score += self._get_rank_score()
        return min(score, 1.0)

    def _get_new_account_score(self) -> float:
        """Calculate new account factor for smurf detection.

        :returns: 0.3 if new account, 0.0 otherwise
        """
        return 0.3 if self.is_new_account() else 0.0

    def _get_win_rate_score(self) -> float:
        """Calculate win rate factor for smurf detection.

        :returns: 0.0-0.4 based on win rate
        """
        if not self.ranks:
            return 0.0

        current_ranks = [r for r in self.ranks if r.is_current]
        if not current_ranks:
            return 0.0

        highest_rank = max(current_ranks, key=lambda r: r.wins + r.losses)
        return self._evaluate_win_rate(highest_rank.win_rate)

    def _evaluate_win_rate(self, win_rate: float) -> float:
        """Evaluate win rate and return score.

        :param win_rate: Win rate percentage
        :returns: Score based on win rate thresholds
        """
        if self.is_new_account() and win_rate > 65:
            return 0.4
        if win_rate > 70:
            return 0.2
        return 0.0

    def _get_rank_score(self) -> float:
        """Calculate rank factor for smurf detection.

        :returns: 0.3 if high elo on new account, 0.0 otherwise
        """
        if not self.is_new_account() or not self.ranks:
            return 0.0

        current_ranks = [r for r in self.ranks if r.is_current]
        for rank in current_ranks:
            if rank.is_high_elo():
                return 0.3

        return 0.0

    def needs_data_refresh(self, refresh_interval_days: int = 1) -> bool:
        """Determine if player data should be refreshed from Riot API.

        Business rule: Data is stale after refresh_interval_days.

        :param refresh_interval_days: Number of days before data is considered stale
        :returns: True if data needs refresh
        """
        if not self.updated_at:
            return True

        age = datetime.now(timezone.utc) - self.updated_at
        return age.days >= refresh_interval_days

    def validate_for_tracking(self) -> list[str]:
        """Validate that player can be tracked.

        Domain validation rules for business invariants.

        :returns: List of error messages (empty if valid)
        """
        errors = []

        if not self.riot_id or not self.tag_line:
            errors.append("Missing Riot ID - cannot track player without full Riot ID")

        if not self.platform:
            errors.append("Missing platform - cannot track player without platform")

        if not self.summoner_name and not self.summoner_id:
            errors.append("Missing summoner data - fetch from Riot API first")

        return errors

    def mark_as_tracked(self) -> None:
        """Mark player as tracked (business operation).

        This is a domain operation that changes player state.
        """
        self.is_tracked = True

    def unmark_as_tracked(self) -> None:
        """Remove player from tracking (business operation).

        This is a domain operation that changes player state.
        """
        self.is_tracked = False

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<PlayerORM(puuid='{self.puuid}', "
            f"riot_id='{self.riot_id}#{self.tag_line}', "
            f"platform='{self.platform}', "
            f"is_tracked={self.is_tracked})>"
        )


class PlayerRankORM(Base):
    """Player rank information for a specific queue (Rich Domain Model).

    One player can have multiple ranks (Solo/Duo, Flex, etc.).
    Contains both data and rank-specific business logic.
    """

    __tablename__ = "player_ranks"
    __table_args__ = (
        Index("idx_ranks_puuid_queue", "puuid", "queue_type"),
        Index("idx_ranks_tier_rank", "tier", "rank"),
        Index("idx_ranks_queue_current", "queue_type", "is_current"),
        Index("idx_ranks_puuid_current", "puuid", "is_current"),
        Index("idx_ranks_tier_lp", "tier", "league_points"),
        {"schema": "core"},
    )

    # ========================================================================
    # DATABASE FIELDS
    # ========================================================================

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Auto-incrementing primary key",
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
        String(4),
        nullable=True,
        index=True,
        comment="Rank division (I, II, III, IV)",
    )

    league_points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="League points (0-100)",
    )

    wins: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of wins in this queue",
    )

    losses: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of losses in this queue",
    )

    # League status flags
    veteran: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the player is a veteran",
    )

    inactive: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the player is inactive",
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
        String(64),
        nullable=True,
        index=True,
        comment="League ID",
    )

    league_name: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="League name",
    )

    # Season information
    season_id: Mapped[Optional[str]] = mapped_column(
        String(16),
        nullable=True,
        index=True,
        comment="Season identifier",
    )

    # Is current rank flag
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this is the current rank for the player",
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

    # ========================================================================
    # RELATIONSHIPS
    # ========================================================================

    player: Mapped["PlayerORM"] = relationship(back_populates="ranks")

    # ========================================================================
    # RICH DOMAIN MODEL - Business Logic Methods
    # ========================================================================

    @property
    def win_rate(self) -> float:
        """Calculate win rate as a percentage.

        Business calculation on domain data.

        :returns: Win rate as percentage (0-100)
        """
        total_games = self.wins + self.losses
        if total_games == 0:
            return 0.0
        return (self.wins / total_games) * 100

    @property
    def total_games(self) -> int:
        """Get total number of games played.

        :returns: Sum of wins and losses
        """
        return self.wins + self.losses

    @property
    def display_rank(self) -> str:
        """Get human-readable rank (e.g., 'Gold II').

        Business formatting rule.

        :returns: Formatted rank string
        """
        if self.rank:
            return f"{self.tier.title()} {self.rank}"
        return self.tier.title()

    def is_high_elo(self) -> bool:
        """Determine if rank is high elo.

        Business rule: Diamond+ is considered high elo.

        :returns: True if Diamond or above
        """
        return self.tier.upper() in ("DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER")

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<PlayerRankORM(id={self.id}, "
            f"puuid='{self.puuid}', "
            f"rank='{self.display_rank}', "
            f"lp={self.league_points}, "
            f"wr={self.win_rate:.1f}%)>"
        )
