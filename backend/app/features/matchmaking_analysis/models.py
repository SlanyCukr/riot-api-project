"""Matchmaking analysis model for tracking analysis state and results."""

from typing import Optional
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    BigInteger,
    DateTime as SQLDateTime,
    String,
    Text,
    Index,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base


class AnalysisStatus(str, Enum):
    """Status of matchmaking analysis."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MatchmakingAnalysis(Base):
    """Matchmaking analysis model for tracking analysis progress and results."""

    __tablename__ = "matchmaking_analyses"

    # Primary key
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        comment="Auto-incrementing primary key",
    )

    # Foreign key to player
    puuid: Mapped[str] = mapped_column(
        String(78),
        ForeignKey("app.players.puuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Player PUUID this analysis is for",
    )

    # Analysis status and progress
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AnalysisStatus.PENDING.value,
        index=True,
        comment="Current status of the analysis",
    )

    progress: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        comment="Number of API requests completed",
    )

    total_requests: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=1000,
        comment="Estimated total API requests needed",
    )

    # Time estimation
    estimated_minutes_remaining: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=20,
        comment="Estimated minutes remaining for completion",
    )

    # Results - stored as JSON for flexibility
    results: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Analysis results as JSON (team/enemy winrates)",
    )

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if analysis failed",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this analysis was created",
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=True,
        comment="When this analysis was started",
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=True,
        comment="When this analysis was completed",
    )

    updated_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="When this analysis record was last updated",
    )

    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_matchmaking_analyses_puuid_status", "puuid", "status"),
        Index("ix_matchmaking_analyses_created_at", "created_at"),
        {"schema": "app"},
    )

    def __repr__(self) -> str:
        """String representation of the analysis."""
        return (
            f"<MatchmakingAnalysis(id={self.id}, puuid={self.puuid}, "
            f"status={self.status}, progress={self.progress}/{self.total_requests})>"
        )
