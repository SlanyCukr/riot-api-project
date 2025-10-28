"""Match participant model for storing individual player performance in matches."""

from decimal import Decimal
from typing import Optional
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime as SQLDateTime,
    ForeignKey,
    Index,
    Numeric as SQLDecimal,
    String,
)
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel


class MatchParticipantBase(SQLModel):
    """Base match participant schema with shared fields."""

    # Participant information
    summoner_name: Optional[str] = Field(
        default=None,
        max_length=32,
        description="Summoner name at the time of the match (may be NULL if Riot API returns empty string)",
    )

    summoner_level: int = Field(
        default=1,
        description="Summoner level at the time of the match",
    )

    team_id: int = Field(
        index=True,
        description="Team ID (100 for blue side, 200 for red side)",
    )

    # Champion information
    champion_id: int = Field(
        index=True,
        description="Champion ID played by the participant",
    )

    champion_name: str = Field(
        max_length=32,
        index=True,
        description="Champion name played by the participant",
    )

    # Performance statistics
    kills: int = Field(default=0, description="Number of kills")
    deaths: int = Field(default=0, description="Number of deaths")
    assists: int = Field(default=0, description="Number of assists")
    win: bool = Field(description="Whether the participant won the match")
    gold_earned: int = Field(default=0, description="Total gold earned")
    vision_score: int = Field(default=0, description="Vision score")
    cs: int = Field(default=0, description="Total creep score (minions killed)")

    kda: Optional[Decimal] = Field(
        default=None,
        description="Kill-death-assist ratio",
        sa_column=Column(SQLDecimal(5, 2), nullable=True),
    )

    # Additional performance metrics
    champ_level: int = Field(default=1, description="Champion level achieved")

    total_damage_dealt: int = Field(
        default=0,
        description="Total damage dealt",
        sa_column=Column(BigInteger, nullable=False, default=0),
    )

    total_damage_dealt_to_champions: int = Field(
        default=0,
        description="Total damage dealt to champions",
        sa_column=Column(BigInteger, nullable=False, default=0),
    )

    total_damage_taken: int = Field(
        default=0,
        description="Total damage taken",
        sa_column=Column(BigInteger, nullable=False, default=0),
    )

    total_heal: int = Field(
        default=0,
        description="Total healing done",
        sa_column=Column(BigInteger, nullable=False, default=0),
    )

    # Position information
    individual_position: Optional[str] = Field(
        default=None,
        max_length=16,
        index=True,
        description="Individual position (e.g., 'TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY')",
    )

    team_position: Optional[str] = Field(
        default=None,
        max_length=16,
        index=True,
        description="Team position",
    )

    # Role information
    role: Optional[str] = Field(
        default=None,
        max_length=16,
        index=True,
        description="Role (e.g., 'DUO', 'DUO_CARRY', 'DUO_SUPPORT', 'SUPPORT')",
    )

    # Player identity fields at time of match (from Riot API)
    riot_id_name: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Riot ID game name at the time of the match",
    )

    riot_id_tagline: Optional[str] = Field(
        default=None,
        max_length=32,
        description="Riot ID tagline at the time of the match",
    )


class MatchParticipant(MatchParticipantBase, table=True):
    """Match participant model storing individual player performance data."""

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

    # Primary key - auto-increment BigInteger
    id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True),
        description="Auto-incrementing primary key",
    )

    # Foreign keys
    match_id: str = Field(
        description="Reference to the match this participant belongs to",
        sa_column=Column(
            String(64),
            ForeignKey("core.matches.match_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )

    puuid: str = Field(
        description="Reference to the player (Riot PUUID)",
        sa_column=Column(
            String(78),
            ForeignKey("core.players.puuid", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )

    # Timestamps - let PostgreSQL handle defaults
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            SQLDateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
        description="When this participant record was created",
    )

    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            SQLDateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
        description="When this participant record was last updated",
    )

    # Relationships
    match: "Match" = Relationship(back_populates="participants")

    # Player relationship - now enabled after SQLModel migration
    player: "Player" = Relationship(back_populates="match_participations")

    def __repr__(self) -> str:
        """Return string representation of the match participant."""
        return f"<MatchParticipant(match_id='{self.match_id}', summoner_name='{self.summoner_name}', champion='{self.champion_name}')>"
