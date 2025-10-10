"""Match participant model for storing individual player performance in matches."""

from decimal import Decimal
from typing import Optional
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime as SQLDateTime,
    Numeric as SQLDecimal,
    ForeignKey,
    Integer,
    String,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from . import Base


class MatchParticipant(Base):
    """Match participant model storing individual player performance data."""

    __tablename__ = "match_participants"

    # Primary key
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, comment="Auto-incrementing primary key"
    )

    # Foreign keys
    match_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("matches.match_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the match this participant belongs to",
    )

    puuid: Mapped[str] = mapped_column(
        String(78),
        ForeignKey("players.puuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the player (Riot PUUID)",
    )

    # Participant information
    summoner_name: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="Summoner name at the time of the match"
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
        Integer, nullable=False, default=0, comment="Number of kills"
    )

    deaths: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Number of deaths"
    )

    assists: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Number of assists"
    )

    win: Mapped[bool] = mapped_column(
        Boolean, nullable=False, comment="Whether the participant won the match"
    )

    gold_earned: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Total gold earned"
    )

    vision_score: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Vision score"
    )

    cs: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Total creep score (minions killed)"
    )

    kda: Mapped[Optional[Decimal]] = mapped_column(
        SQLDecimal(5, 2), nullable=True, comment="Kill-death-assist ratio"
    )

    # Additional performance metrics
    champ_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="Champion level achieved"
    )

    total_damage_dealt: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, comment="Total damage dealt"
    )

    total_damage_dealt_to_champions: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, comment="Total damage dealt to champions"
    )

    total_damage_taken: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, comment="Total damage taken"
    )

    total_heal: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, comment="Total healing done"
    )

    # Position information
    individual_position: Mapped[Optional[str]] = mapped_column(
        String(16),
        nullable=True,
        index=True,
        comment="Individual position (e.g., 'TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY')",
    )

    team_position: Mapped[Optional[str]] = mapped_column(
        String(16), nullable=True, index=True, comment="Team position"
    )

    # Role information
    role: Mapped[Optional[str]] = mapped_column(
        String(16),
        nullable=True,
        index=True,
        comment="Role (e.g., 'DUO', 'DUO_CARRY', 'DUO_SUPPORT', 'SUPPORT')",
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

    # Relationships
    match = relationship("Match", back_populates="participants")
    player = relationship("Player", back_populates="match_participations")

    def __repr__(self) -> str:
        """Return string representation of the match participant."""
        return f"<MatchParticipant(match_id='{self.match_id}', summoner_name='{self.summoner_name}', champion='{self.champion_name}')>"

    def to_dict(self) -> dict:
        """Convert match participant to dictionary representation."""
        return {
            "id": self.id,
            "match_id": self.match_id,
            "puuid": str(self.puuid),
            "summoner_name": self.summoner_name,
            "team_id": self.team_id,
            "champion_id": self.champion_id,
            "champion_name": self.champion_name,
            "kills": self.kills,
            "deaths": self.deaths,
            "assists": self.assists,
            "win": self.win,
            "gold_earned": self.gold_earned,
            "vision_score": self.vision_score,
            "cs": self.cs,
            "kda": float(self.kda) if self.kda else None,
            "champ_level": self.champ_level,
            "total_damage_dealt": self.total_damage_dealt,
            "total_damage_dealt_to_champions": self.total_damage_dealt_to_champions,
            "total_damage_taken": self.total_damage_taken,
            "total_heal": self.total_heal,
            "individual_position": self.individual_position,
            "team_position": self.team_position,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def calculate_kda(self) -> Decimal:
        """Calculate KDA ratio (kills + assists) / deaths, with deaths=0 treated as 1."""
        if self.deaths == 0:
            return Decimal(self.kills + self.assists)
        return Decimal(self.kills + self.assists) / Decimal(self.deaths)

    def calculate_cs_per_minute(self) -> Optional[float]:
        """Calculate CS per minute."""
        # This would need to be calculated after fetching the match
        # For now, we'll return None
        return None

    @property
    def kdr(self) -> Optional[float]:
        """Kill-death ratio."""
        if self.deaths == 0:
            return float(self.kills)
        return self.kills / self.deaths

    @property
    def total_kills_participation(self) -> int:
        """Total kills participated in (kills + assists)."""
        return self.kills + self.assists


# Create composite indexes for common queries
Index("idx_participants_match_puuid", MatchParticipant.match_id, MatchParticipant.puuid)

Index(
    "idx_participants_champion_win", MatchParticipant.champion_id, MatchParticipant.win
)

Index("idx_participants_kills_deaths", MatchParticipant.kills, MatchParticipant.deaths)

Index(
    "idx_participants_position_champion",
    MatchParticipant.individual_position,
    MatchParticipant.champion_id,
)

Index("idx_participants_team_win", MatchParticipant.team_id, MatchParticipant.win)
