"""Matchmaking analysis model for tracking analysis state and results.

SQLModel implementation following the pattern:
- Base models: Shared fields between database and API
- Table models: Database tables with table=True
- API models: Request/response schemas (if needed)
"""

from typing import Optional
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime as SQLDateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel
from pydantic import ConfigDict


class AnalysisStatus(str, Enum):
    """Status of matchmaking analysis."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# BASE MODELS - Shared fields between table and API
# ============================================================================


class MatchmakingAnalysisBase(SQLModel):
    """Base matchmaking analysis schema with shared fields."""

    # Analysis progress
    progress: int = Field(
        default=0,
        sa_column=Column(BigInteger, nullable=False, default=0),
        description="Number of API requests completed",
    )

    total_requests: int = Field(
        default=1000,
        sa_column=Column(BigInteger, nullable=False, default=1000),
        description="Estimated total API requests needed",
    )

    # Time estimation
    estimated_minutes_remaining: int = Field(
        default=20,
        sa_column=Column(BigInteger, nullable=False, default=20),
        description="Estimated minutes remaining for completion",
    )


# ============================================================================
# TABLE MODELS - Database tables
# ============================================================================


class MatchmakingAnalysis(MatchmakingAnalysisBase, table=True):
    """Matchmaking analysis model for tracking analysis progress and results."""

    __tablename__ = "matchmaking_analyses"
    __table_args__ = (
        Index("ix_matchmaking_analyses_puuid_status", "puuid", "status"),
        Index("ix_matchmaking_analyses_created_at", "created_at"),
        {"schema": "core"},
    )

    # Primary key
    id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True),
        description="Auto-incrementing primary key",
    )

    # Foreign key to player
    puuid: str = Field(
        sa_column=Column(
            String(78),
            ForeignKey("core.players.puuid", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        description="Player PUUID this analysis is for",
    )

    # Analysis status
    status: str = Field(
        default=AnalysisStatus.PENDING.value,
        max_length=20,
        index=True,
        description="Current status of the analysis",
    )

    # Results - stored as JSON for flexibility
    results: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Analysis results as JSON (team/enemy winrates)",
    )

    # Error tracking
    error_message: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Error message if analysis failed",
    )

    # Timestamps
    created_at: datetime = Field(
        default=None,
        sa_column=Column(
            SQLDateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
        description="When this analysis was created",
    )

    started_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            SQLDateTime(timezone=True),
            nullable=True,
        ),
        description="When this analysis was started",
    )

    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            SQLDateTime(timezone=True),
            nullable=True,
        ),
        description="When this analysis was completed",
    )

    updated_at: datetime = Field(
        default=None,
        sa_column=Column(
            SQLDateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
        description="When this analysis record was last updated",
    )

    model_config = ConfigDict(from_attributes=True)

    def __repr__(self) -> str:
        """String representation of the analysis."""
        return (
            f"<MatchmakingAnalysis(id={self.id}, puuid={self.puuid}, "
            f"status={self.status}, progress={self.progress}/{self.total_requests})>"
        )
