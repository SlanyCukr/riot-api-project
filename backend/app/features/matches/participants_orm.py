"""SQLAlchemy 2.0 ORM models for match participants with Rich Domain Model pattern.

This module defines database models for individual player performance in matches,
following Martin Fowler's Rich Domain Model pattern with business logic methods.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime as SQLDateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric as SQLDecimal,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.models import Base

if TYPE_CHECKING:
    from app.features.matches.orm_models import MatchORM
    from app.features.players.orm_models import PlayerORM


class MatchParticipantORM(Base):
    """Match participant domain model (Rich Domain Model pattern).

    Combines data and behavior:
    - Database fields with type safety (SQLAlchemy 2.0 Mapped types)
    - Business logic methods (KDA calculation, performance analysis, etc.)
    - Domain calculations and rules
    """

    __tablename__ = "match_participants"
    __table_args__ = (
        Index("idx_participants_match_puuid", "match_id", "puuid"),
        Index("idx_participants_champion_win", "champion_id", "win"),
        Index("idx_participants_kills_deaths", "kills", "deaths"),
        Index(
            "idx_participants_position_champion", "individual_position", "champion_id"
        ),
        Index("idx_participants_team_win", "team_id", "win"),
        {"schema": "core"},
    )

    # ========================================================================
    # DATABASE FIELDS
    # ========================================================================

    # Primary key
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="Auto-incrementing primary key",
    )

    # Foreign keys
    match_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("core.matches.match_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the match this participant belongs to",
    )

    puuid: Mapped[str] = mapped_column(
        String(78),
        ForeignKey("core.players.puuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the player (Riot PUUID)",
    )

    # Participant information
    summoner_name: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="Summoner name at the time of the match (may be NULL if Riot API returns empty string)",
    )

    summoner_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Summoner level at the time of the match",
    )

    team_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Team ID (100 for blue side, 200 for red side)",
    )

    # Champion information
    champion_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Champion ID played by the participant",
    )

    champion_name: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="Champion name played by the participant",
    )

    # Performance statistics
    kills: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of kills",
    )

    deaths: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of deaths",
    )

    assists: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of assists",
    )

    win: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="Whether the participant won the match",
    )

    gold_earned: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total gold earned",
    )

    vision_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Vision score",
    )

    cs: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total creep score (minions killed)",
    )

    kda: Mapped[Optional[Decimal]] = mapped_column(
        SQLDecimal(5, 2),
        nullable=True,
        comment="Kill-death-assist ratio",
    )

    # Additional performance metrics
    champ_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Champion level achieved",
    )

    total_damage_dealt: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        comment="Total damage dealt",
    )

    total_damage_dealt_to_champions: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        comment="Total damage dealt to champions",
    )

    total_damage_taken: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        comment="Total damage taken",
    )

    total_heal: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        comment="Total healing done",
    )

    # Position information
    individual_position: Mapped[Optional[str]] = mapped_column(
        String(16),
        nullable=True,
        index=True,
        comment="Individual position (e.g., 'TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY')",
    )

    team_position: Mapped[Optional[str]] = mapped_column(
        String(16),
        nullable=True,
        index=True,
        comment="Team position",
    )

    # Role information
    role: Mapped[Optional[str]] = mapped_column(
        String(16),
        nullable=True,
        index=True,
        comment="Role (e.g., 'DUO', 'DUO_CARRY', 'DUO_SUPPORT', 'SUPPORT')",
    )

    # Player identity fields at time of match (from Riot API)
    riot_id_name: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="Riot ID game name at the time of the match",
    )

    riot_id_tagline: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="Riot ID tagline at the time of the match",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this participant record was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="When this participant record was last updated",
    )

    # ========================================================================
    # RELATIONSHIPS
    # ========================================================================

    # Type-safe relationships with Mapped
    match: Mapped["MatchORM"] = relationship(
        "MatchORM",
        back_populates="participants",
    )

    player: Mapped["PlayerORM"] = relationship(
        "PlayerORM",
        back_populates="match_participations",
        foreign_keys=[puuid],
    )

    # ========================================================================
    # RICH DOMAIN MODEL - Business Logic Methods
    # ========================================================================

    @staticmethod
    def aggregate_participant_stats(
        matches: list["MatchORM"],
        participants_by_match: dict[str, "MatchParticipantORM"],
    ) -> tuple[int, int, int, int, int, int]:
        """Aggregate statistics from match participants.

        Business logic to calculate total stats across multiple matches for a player.

        :param matches: List of MatchORM objects
        :param participants_by_match: Dictionary mapping match_id to MatchParticipantORM
        :returns: Tuple of (kills, deaths, assists, cs, vision, wins)
        """
        totals = {
            "kills": 0,
            "deaths": 0,
            "assists": 0,
            "cs": 0,
            "vision": 0,
            "wins": 0,
        }

        for match in matches:
            participant = participants_by_match.get(match.match_id)
            if participant:
                totals["kills"] += participant.kills
                totals["deaths"] += participant.deaths
                totals["assists"] += participant.assists
                totals["cs"] += participant.cs
                totals["vision"] += participant.vision_score
                if participant.win:
                    totals["wins"] += 1

        return (
            totals["kills"],
            totals["deaths"],
            totals["assists"],
            totals["cs"],
            totals["vision"],
            totals["wins"],
        )

    def calculate_kda(self) -> float:
        """Calculate KDA (Kill-Death-Assist) ratio.

        Business rule: (kills + assists) / deaths
        If deaths is 0, return kills + assists (perfect KDA).

        :returns: KDA ratio as float
        """
        if self.deaths == 0:
            return float(self.kills + self.assists)
        return (self.kills + self.assists) / self.deaths

    @staticmethod
    def calculate_kda_from_values(kills: int, deaths: int, assists: int) -> float:
        """Calculate KDA (Kill-Death-Assist) ratio from raw values.

        Business rule: (kills + assists) / deaths
        If deaths is 0, return kills + assists (perfect KDA).

        :param kills: Number of kills
        :param deaths: Number of deaths
        :param assists: Number of assists
        :returns: KDA ratio as float
        """
        if deaths == 0:
            return float(kills + assists)
        return (kills + assists) / deaths

    def is_carry_performance(self) -> bool:
        """Determine if this was a carry performance.

        Business rule: High impact performance is defined as:
        - KDA >= 3.0 AND
        - Kills >= 10

        :returns: True if performance meets carry criteria
        """
        return self.calculate_kda() >= 3.0 and self.kills >= 10

    def get_cs_per_minute(self) -> float:
        """Calculate CS (Creep Score) per minute.

        Business calculation: Total CS divided by game duration in minutes.
        Requires the match relationship to be loaded.

        :returns: CS per minute, or 0.0 if match not loaded or duration is 0
        """
        if not self.match:
            return 0.0

        duration_minutes = self.match.get_duration_minutes()
        if duration_minutes == 0:
            return 0.0

        return self.cs / duration_minutes

    def calculate_kill_participation(self, team_kills: int) -> float:
        """Calculate kill participation percentage.

        Business rule: (kills + assists) / team_kills
        Represents how involved the player was in their team's kills.

        :param team_kills: Total kills by the player's team
        :returns: Kill participation as percentage (0-100), or 0.0 if team has no kills
        """
        if team_kills == 0:
            return 0.0

        participation = (self.kills + self.assists) / team_kills
        return participation * 100.0

    def is_support_role(self) -> bool:
        """Check if player is playing support role.

        Business rule: Individual position is 'UTILITY' (modern support designation).

        :returns: True if playing support/utility role
        """
        return self.individual_position == "UTILITY"

    def is_high_vision(self) -> bool:
        """Determine if player has high vision score.

        Business rule: Vision score >= 40 is considered high.
        Used to identify supportive play patterns.

        :returns: True if vision score meets threshold
        """
        return self.vision_score >= 40

    def is_perfect_kda(self) -> bool:
        """Check if player achieved perfect KDA (no deaths).

        Business rule: 0 deaths with at least 1 kill or assist.

        :returns: True if perfect KDA
        """
        return self.deaths == 0 and (self.kills > 0 or self.assists > 0)

    def get_damage_share(self, team_total_damage: int) -> float:
        """Calculate damage share percentage within team.

        Business calculation: Player's damage as percentage of team total.

        :param team_total_damage: Total damage dealt by team to champions
        :returns: Damage share as percentage (0-100), or 0.0 if team total is 0
        """
        if team_total_damage == 0:
            return 0.0

        share = self.total_damage_dealt_to_champions / team_total_damage
        return share * 100.0

    def is_good_cs(self) -> bool:
        """Determine if CS per minute is good.

        Business rule:
        - Support role: Not evaluated (supports don't farm)
        - Other roles: >= 6 CS/min is considered good

        :returns: True if CS/min meets good threshold, or if support role
        """
        if self.is_support_role():
            return True  # Supports don't need high CS

        return self.get_cs_per_minute() >= 6.0

    def get_performance_grade(self) -> str:
        """Calculate overall performance grade.

        Business logic combining multiple factors:
        - Win/loss
        - KDA ratio
        - Carry performance

        :returns: Performance grade (S, A, B, C, D)
        """
        kda = self.calculate_kda()

        if self.is_carry_performance() and self.win:
            return "S"
        if kda >= 3.0 and self.win:
            return "A"
        if kda >= 2.0 or self.win:
            return "B"
        if kda >= 1.0:
            return "C"
        return "D"

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<MatchParticipantORM(id={self.id}, "
            f"match_id='{self.match_id}', "
            f"summoner='{self.summoner_name}', "
            f"champion='{self.champion_name}', "
            f"kda={self.calculate_kda():.2f}, "
            f"win={self.win})>"
        )
