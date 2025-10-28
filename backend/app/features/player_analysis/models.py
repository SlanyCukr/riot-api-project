"""Player analysis model for storing player analysis results and signals."""

from decimal import Decimal
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime as SQLDateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel


class PlayerAnalysisBase(SQLModel):
    """Base player analysis schema with shared fields."""

    # Detection results
    is_smurf: bool = Field(
        default=False,
        index=True,
        description="Whether the player is detected as a smurf",
    )

    confidence: Optional[str] = Field(
        default=None,
        max_length=32,
        index=True,
        description="Confidence level in the player analysis",
    )

    smurf_score: Decimal = Field(
        default=Decimal("0.0"),
        description="Overall smurf score (0.0-1.0)",
        sa_column=Column(Numeric(5, 3), nullable=False, default=0.0, index=True),
    )

    # Signal breakdown - 9 factor scores
    win_rate_score: Optional[Decimal] = Field(
        default=None,
        description="Win rate based smurf score component",
        sa_column=Column(Numeric(5, 3), nullable=True),
    )

    kda_score: Optional[Decimal] = Field(
        default=None,
        description="KDA based smurf score component",
        sa_column=Column(Numeric(5, 3), nullable=True),
    )

    account_level_score: Optional[Decimal] = Field(
        default=None,
        description="Account level based smurf score component",
        sa_column=Column(Numeric(5, 3), nullable=True),
    )

    rank_discrepancy_score: Optional[Decimal] = Field(
        default=None,
        description="Rank discrepancy based smurf score component",
        sa_column=Column(Numeric(5, 3), nullable=True),
    )

    rank_progression_score: Optional[Decimal] = Field(
        default=None,
        description="Rank progression based smurf score component",
        sa_column=Column(Numeric(5, 3), nullable=True),
    )

    win_rate_trend_score: Optional[Decimal] = Field(
        default=None,
        description="Win rate trend based smurf score component",
        sa_column=Column(Numeric(5, 3), nullable=True),
    )

    performance_consistency_score: Optional[Decimal] = Field(
        default=None,
        description="Performance consistency based smurf score component",
        sa_column=Column(Numeric(5, 3), nullable=True),
    )

    performance_trends_score: Optional[Decimal] = Field(
        default=None,
        description="Performance trends based smurf score component",
        sa_column=Column(Numeric(5, 3), nullable=True),
    )

    role_performance_score: Optional[Decimal] = Field(
        default=None,
        description="Role performance based smurf score component",
        sa_column=Column(Numeric(5, 3), nullable=True),
    )

    # Analysis parameters
    games_analyzed: int = Field(
        default=0,
        description="Number of games analyzed for this detection",
    )

    queue_type: Optional[str] = Field(
        default=None,
        max_length=32,
        index=True,
        description="Queue type analyzed (e.g., RANKED_SOLO_5x5)",
    )

    time_period_days: Optional[int] = Field(
        default=None,
        description="Time period in days analyzed",
    )

    # Detection thresholds
    win_rate_threshold: Optional[Decimal] = Field(
        default=None,
        description="Win rate threshold used for detection",
        sa_column=Column(Numeric(5, 3), nullable=True),
    )

    kda_threshold: Optional[Decimal] = Field(
        default=None,
        description="KDA threshold used for detection",
        sa_column=Column(Numeric(5, 3), nullable=True),
    )

    # Additional signals
    account_level: Optional[int] = Field(
        default=None,
        description="Account level at time of analysis",
    )

    current_tier: Optional[str] = Field(
        default=None,
        max_length=16,
        description="Current tier at time of analysis",
    )

    current_rank: Optional[str] = Field(
        default=None,
        max_length=4,
        description="Current rank at time of analysis",
    )

    peak_tier: Optional[str] = Field(
        default=None,
        max_length=16,
        description="Peak tier observed",
    )

    peak_rank: Optional[str] = Field(
        default=None,
        max_length=4,
        description="Peak rank observed",
    )

    # Metadata
    analysis_version: Optional[str] = Field(
        default=None,
        max_length=16,
        description="Version of the player analysis algorithm",
    )

    false_positive_reported: bool = Field(
        default=False,
        index=True,
        description="Whether this detection was reported as false positive",
    )

    manually_verified: bool = Field(
        default=False,
        index=True,
        description="Whether this detection was manually verified",
    )

    notes: Optional[str] = Field(
        default=None,
        description="Additional notes about this detection",
        sa_column=Column(Text, nullable=True),
    )


class PlayerAnalysis(PlayerAnalysisBase, table=True):
    """Player analysis model storing detection results and signals for smurfs, boosted accounts, and trolls."""

    __tablename__ = "player_analysis"
    __table_args__ = (
        Index("idx_player_analysis_puuid_confidence", "puuid", "confidence"),
        Index("idx_player_analysis_is_smurf_score", "is_smurf", "smurf_score"),
        Index("idx_player_analysis_queue_score", "queue_type", "smurf_score"),
        Index("idx_player_analysis_analysis_time", "last_analysis", "is_smurf"),
        Index(
            "idx_player_analysis_false_positive", "false_positive_reported", "is_smurf"
        ),
        {"schema": "core"},
    )

    # Primary key - auto-increment
    id: Optional[int] = Field(
        default=None,
        primary_key=True,
        description="Auto-incrementing primary key",
    )

    # Foreign key - CASCADE delete
    puuid: str = Field(
        description="Reference to the player being analyzed (Riot PUUID)",
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
        description="When this player analysis was created",
    )

    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            SQLDateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
        description="When this player analysis was last updated",
    )

    last_analysis: datetime | None = Field(
        default=None,
        sa_column=Column(
            SQLDateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            index=True,
        ),
        description="When the last analysis was performed",
    )

    # Relationships
    # Player relationship - now enabled after SQLModel migration
    player: Optional["Player"] = Relationship(back_populates="player_analyses")

    def __repr__(self) -> str:
        """Return string representation of the player analysis."""
        return f"<PlayerAnalysis(puuid='{self.puuid}', is_smurf={self.is_smurf}, confidence='{self.confidence}')>"
