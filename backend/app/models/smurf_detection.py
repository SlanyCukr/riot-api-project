"""Smurf detection model for storing player analysis results and signals."""

from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean,
    DateTime as SQLDateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from . import Base


class SmurfDetection(Base):
    """Smurf detection model storing detection results and signals."""

    __tablename__ = "smurf_detections"

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="Auto-incrementing primary key"
    )

    # Foreign key
    puuid: Mapped[str] = mapped_column(
        String(78),
        ForeignKey("players.puuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the player being analyzed (Riot PUUID)",
    )

    # Detection results
    is_smurf: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether the player is detected as a smurf",
    )

    confidence: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        index=True,
        comment="Confidence level in the player analysis",
    )

    smurf_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 3),
        nullable=False,
        default=0.0,
        index=True,
        comment="Overall smurf score (0.0-1.0)",
    )

    # Signal breakdown
    win_rate_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 3), nullable=True, comment="Win rate based smurf score component"
    )

    kda_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 3), nullable=True, comment="KDA based smurf score component"
    )

    account_level_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 3),
        nullable=True,
        comment="Account level based smurf score component",
    )

    rank_discrepancy_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 3),
        nullable=True,
        comment="Rank discrepancy based smurf score component",
    )

    rank_progression_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 3),
        nullable=True,
        comment="Rank progression based smurf score component",
    )

    win_rate_trend_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 3),
        nullable=True,
        comment="Win rate trend based smurf score component",
    )

    performance_consistency_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 3),
        nullable=True,
        comment="Performance consistency based smurf score component",
    )

    performance_trends_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 3),
        nullable=True,
        comment="Performance trends based smurf score component",
    )

    role_performance_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 3),
        nullable=True,
        comment="Role performance based smurf score component",
    )

    # Analysis parameters
    games_analyzed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of games analyzed for this detection",
    )

    queue_type: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        index=True,
        comment="Queue type analyzed (e.g., RANKED_SOLO_5x5)",
    )

    time_period_days: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Time period in days analyzed"
    )

    # Detection thresholds
    win_rate_threshold: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 3), nullable=True, comment="Win rate threshold used for detection"
    )

    kda_threshold: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 3), nullable=True, comment="KDA threshold used for detection"
    )

    # Additional signals
    account_level: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Account level at time of analysis"
    )

    current_tier: Mapped[Optional[str]] = mapped_column(
        String(16), nullable=True, comment="Current tier at time of analysis"
    )

    current_rank: Mapped[Optional[str]] = mapped_column(
        String(4), nullable=True, comment="Current rank at time of analysis"
    )

    peak_tier: Mapped[Optional[str]] = mapped_column(
        String(16), nullable=True, comment="Peak tier observed"
    )

    peak_rank: Mapped[Optional[str]] = mapped_column(
        String(4), nullable=True, comment="Peak rank observed"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this player analysis was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="When this player analysis was last updated",
    )

    last_analysis: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="When the last analysis was performed",
    )

    # Metadata
    analysis_version: Mapped[Optional[str]] = mapped_column(
        String(16), nullable=True, comment="Version of the player analysis algorithm"
    )

    false_positive_reported: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether this detection was reported as false positive",
    )

    manually_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether this detection was manually verified",
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Additional notes about this detection"
    )

    # Relationships
    player = relationship("Player", back_populates="smurf_detections")

    def __repr__(self) -> str:
        """Return string representation of the player analysis."""
        return f"<SmurfDetection(puuid='{self.puuid}', is_smurf={self.is_smurf}, confidence='{self.confidence}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert player analysis to dictionary representation."""
        return {
            "id": self.id,
            "puuid": str(self.puuid),
            "is_smurf": self.is_smurf,
            "confidence": self.confidence,
            "smurf_score": float(self.smurf_score) if self.smurf_score else 0.0,
            "win_rate_score": (
                float(self.win_rate_score) if self.win_rate_score else None
            ),
            "kda_score": float(self.kda_score) if self.kda_score else None,
            "account_level_score": (
                float(self.account_level_score) if self.account_level_score else None
            ),
            "rank_discrepancy_score": (
                float(self.rank_discrepancy_score)
                if self.rank_discrepancy_score
                else None
            ),
            "rank_progression_score": (
                float(self.rank_progression_score)
                if self.rank_progression_score
                else None
            ),
            "win_rate_trend_score": (
                float(self.win_rate_trend_score) if self.win_rate_trend_score else None
            ),
            "performance_consistency_score": (
                float(self.performance_consistency_score)
                if self.performance_consistency_score
                else None
            ),
            "performance_trends_score": (
                float(self.performance_trends_score)
                if self.performance_trends_score
                else None
            ),
            "role_performance_score": (
                float(self.role_performance_score)
                if self.role_performance_score
                else None
            ),
            "games_analyzed": self.games_analyzed,
            "queue_type": self.queue_type,
            "time_period_days": self.time_period_days,
            "win_rate_threshold": (
                float(self.win_rate_threshold) if self.win_rate_threshold else None
            ),
            "kda_threshold": float(self.kda_threshold) if self.kda_threshold else None,
            "account_level": self.account_level,
            "current_tier": self.current_tier,
            "current_rank": self.current_rank,
            "peak_tier": self.peak_tier,
            "peak_rank": self.peak_rank,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_analysis": (
                self.last_analysis.isoformat() if self.last_analysis else None
            ),
            "analysis_version": self.analysis_version,
            "false_positive_reported": self.false_positive_reported,
            "manually_verified": self.manually_verified,
            "notes": self.notes,
        }


# Create composite indexes for common queries
Index(
    "idx_smurf_detection_puuid_confidence",
    SmurfDetection.puuid,
    SmurfDetection.confidence,
)

Index(
    "idx_smurf_detection_is_smurf_score",
    SmurfDetection.is_smurf,
    SmurfDetection.smurf_score,
)

Index(
    "idx_smurf_detection_queue_score",
    SmurfDetection.queue_type,
    SmurfDetection.smurf_score,
)

Index(
    "idx_smurf_detection_analysis_time",
    SmurfDetection.last_analysis,
    SmurfDetection.is_smurf,
)

Index(
    "idx_smurf_detection_false_positive",
    SmurfDetection.false_positive_reported,
    SmurfDetection.is_smurf,
)
