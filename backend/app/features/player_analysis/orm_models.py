"""SQLAlchemy 2.0 ORM models for player analysis feature with Rich Domain Model pattern.

This module defines database models following Martin Fowler's Rich Domain Model pattern,
where business logic and behavior are combined with data in domain objects.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, TYPE_CHECKING, List

from sqlalchemy import (
    Boolean,
    DateTime as SQLDateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.models import Base

if TYPE_CHECKING:
    from app.features.players.orm_models import PlayerORM


class PlayerAnalysisORM(Base):
    """Player analysis domain model (Rich Domain Model pattern).

    Combines data and behavior:
    - Database fields with type safety (SQLAlchemy 2.0 Mapped types)
    - Business logic methods (validation, calculations, analysis helpers)
    - Domain calculations and rules
    """

    __tablename__ = "player_analysis"
    __table_args__ = (
        Index(
            "idx_player_analysis_puuid_confidence",
            "puuid",
            "confidence",
        ),
        Index(
            "idx_player_analysis_is_smurf_score",
            "is_smurf",
            "smurf_score",
        ),
        Index(
            "idx_player_analysis_queue_score",
            "queue_type",
            "smurf_score",
        ),
        Index(
            "idx_player_analysis_analysis_time",
            "last_analysis",
            "is_smurf",
        ),
        Index(
            "idx_player_analysis_false_positive",
            "false_positive_reported",
            "is_smurf",
        ),
        {"schema": "core", "extend_existing": True},
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
        Numeric(5, 3),
        nullable=True,
        comment="Win rate based smurf score component",
    )

    kda_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 3),
        nullable=True,
        comment="KDA based smurf score component",
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
        Integer,
        nullable=True,
        comment="Time period in days analyzed",
    )

    # Detection thresholds
    win_rate_threshold: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 3),
        nullable=True,
        comment="Win rate threshold used for detection",
    )

    kda_threshold: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 3),
        nullable=True,
        comment="KDA threshold used for detection",
    )

    # Additional signals
    account_level: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Account level at time of analysis",
    )

    current_tier: Mapped[Optional[str]] = mapped_column(
        String(16),
        nullable=True,
        comment="Current tier at time of analysis",
    )

    current_rank: Mapped[Optional[str]] = mapped_column(
        String(4),
        nullable=True,
        comment="Current rank at time of analysis",
    )

    peak_tier: Mapped[Optional[str]] = mapped_column(
        String(16),
        nullable=True,
        comment="Peak tier observed",
    )

    peak_rank: Mapped[Optional[str]] = mapped_column(
        String(4),
        nullable=True,
        comment="Peak rank observed",
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
        String(16),
        nullable=True,
        comment="Version of the player analysis algorithm",
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
        Text,
        nullable=True,
        comment="Additional notes about this detection",
    )

    # ========================================================================
    # RELATIONSHIPS
    # ========================================================================

    # Type-safe relationship with Mapped
    player: Mapped["PlayerORM"] = relationship(
        back_populates="player_analyses",
        foreign_keys=[puuid],
    )

    # ========================================================================
    # RICH DOMAIN MODEL - Business Logic Methods
    # ========================================================================

    def calculate_win_rate_score(self) -> Optional[float]:
        """Calculate win rate score from stored signal.

        Business logic: Returns the win_rate_score as a float if available.

        :returns: Win rate score as float (0.0-1.0) or None if not set
        """
        if self.win_rate_score is None:
            return None
        return float(self.win_rate_score)

    def calculate_kda_score(self) -> Optional[float]:
        """Calculate KDA score from stored signal.

        Business logic: Returns the kda_score as a float if available.

        :returns: KDA score as float (0.0-1.0) or None if not set
        """
        if self.kda_score is None:
            return None
        return float(self.kda_score)

    def is_recent_analysis(self, hours_threshold: int = 24) -> bool:
        """Determine if analysis is recent enough.

        Business rule: Analysis is considered stale after hours_threshold hours.

        :param hours_threshold: Number of hours after which analysis is stale
        :returns: True if analysis is within time window
        """
        if not self.last_analysis:
            return False

        age = datetime.now(timezone.utc) - self.last_analysis
        return age < timedelta(hours=hours_threshold)

    def validate_analysis_data(self) -> list[str]:
        """Validate that analysis has all required data.

        Domain validation rules for business invariants.

        :returns: List of error messages (empty if valid)
        """
        errors = []

        if not self.puuid:
            errors.append("Missing PUUID - cannot analyze player without identifier")

        if self.games_analyzed <= 0:
            errors.append(
                f"Invalid games_analyzed ({self.games_analyzed}) - must be > 0"
            )

        if self.smurf_score < 0.0 or self.smurf_score > 1.0:
            errors.append(
                f"Invalid smurf_score ({self.smurf_score}) - must be between 0.0 and 1.0"
            )

        if self.confidence and self.confidence not in ("high", "medium", "low"):
            errors.append(
                f"Invalid confidence level '{self.confidence}' - must be 'high', 'medium', or 'low'"
            )

        # Validate score fields are in valid range if set
        score_fields = [
            ("win_rate_score", self.win_rate_score),
            ("kda_score", self.kda_score),
            ("account_level_score", self.account_level_score),
            ("rank_discrepancy_score", self.rank_discrepancy_score),
            ("rank_progression_score", self.rank_progression_score),
            ("win_rate_trend_score", self.win_rate_trend_score),
            ("performance_consistency_score", self.performance_consistency_score),
            ("performance_trends_score", self.performance_trends_score),
            ("role_performance_score", self.role_performance_score),
        ]

        for field_name, value in score_fields:
            if value is not None and (value < 0.0 or value > 1.0):
                errors.append(
                    f"Invalid {field_name} ({value}) - must be between 0.0 and 1.0 or None"
                )

        if not self.last_analysis:
            errors.append("Missing last_analysis timestamp")

        return errors

    def get_missing_factors(self) -> List[str]:
        """Identify which analyzers didn't run or have no data.

        Business logic: Returns list of factor names that are None.

        :returns: List of missing factor names
        """
        factor_fields = {
            "win_rate": self.win_rate_score,
            "kda": self.kda_score,
            "account_level": self.account_level_score,
            "rank_discrepancy": self.rank_discrepancy_score,
            "rank_progression": self.rank_progression_score,
            "win_rate_trend": self.win_rate_trend_score,
            "performance_consistency": self.performance_consistency_score,
            "performance_trends": self.performance_trends_score,
            "role_performance": self.role_performance_score,
        }

        return [name for name, value in factor_fields.items() if value is None]

    @property
    def has_complete_analysis(self) -> bool:
        """Check if analysis has all factor scores.

        Business logic: All 9 factors should be present for a complete analysis.

        :returns: True if all factors have been analyzed
        """
        return len(self.get_missing_factors()) == 0

    @property
    def is_high_confidence_detection(self) -> bool:
        """Check if this is a high confidence smurf detection.

        Business logic: High confidence means high score AND marked as smurf.

        :returns: True if high confidence smurf detection
        """
        return self.is_smurf and self.confidence == "high"

    def needs_reanalysis(
        self,
        min_games_threshold: int = 30,
        staleness_threshold_hours: int = 24,
    ) -> bool:
        """Determine if player needs re-analysis.

        Business rule: Analysis is stale if:
        - Too few games analyzed
        - Analysis is old (> staleness_threshold_hours)
        - Analysis is incomplete (missing factors)

        :param min_games_threshold: Minimum games needed for reliable analysis
        :param staleness_threshold_hours: Hours after which analysis is stale
        :returns: True if player needs re-analysis
        """
        if self.games_analyzed < min_games_threshold:
            return True

        if not self.is_recent_analysis(staleness_threshold_hours):
            return True

        if not self.has_complete_analysis:
            return True

        return False

    def get_factor_breakdown(self) -> dict[str, float]:
        """Get all factor scores as a dictionary.

        Business logic: Returns dict of all factor names to their scores.

        :returns: Dictionary mapping factor names to scores (0.0-1.0)
        """
        return {
            "win_rate": self.calculate_win_rate_score() or 0.0,
            "kda": self.calculate_kda_score() or 0.0,
            "account_level": float(self.account_level_score or 0.0),
            "rank_discrepancy": float(self.rank_discrepancy_score or 0.0),
            "rank_progression": float(self.rank_progression_score or 0.0),
            "win_rate_trend": float(self.win_rate_trend_score or 0.0),
            "performance_consistency": float(self.performance_consistency_score or 0.0),
            "performance_trends": float(self.performance_trends_score or 0.0),
            "role_performance": float(self.role_performance_score or 0.0),
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<PlayerAnalysisORM("
            f"id={self.id}, "
            f"puuid='{self.puuid}', "
            f"is_smurf={self.is_smurf}, "
            f"smurf_score={float(self.smurf_score):.3f}, "
            f"confidence='{self.confidence}', "
            f"games_analyzed={self.games_analyzed}"
            f")>"
        )
