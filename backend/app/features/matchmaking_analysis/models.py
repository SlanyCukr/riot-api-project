"""Domain models for matchmaking analysis feature (Pydantic, separate from ORM)."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class MatchmakingAnalysis(BaseModel):
    """Rich domain model for matchmaking analysis job."""

    model_config = ConfigDict(from_attributes=False)

    id: str
    user_id: str
    job_type: str = Field(default="matchmaking_analysis")
    status: str
    parameters: Optional[dict] = None
    result: Optional[dict] = None
    error_message: Optional[str] = None
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Analysis-specific fields
    matches_analyzed: int = Field(default=0, ge=0)
    winrate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    avg_rank_difference: Optional[float] = Field(default=None, ge=0.0)
    fairness_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    # Rich domain methods

    def is_running(self) -> bool:
        """Check if analysis is currently running."""
        return self.status == "running"

    def is_completed(self) -> bool:
        """Check if analysis has completed (successfully or failed)."""
        return self.status in ["completed", "success", "failed"]

    def is_successful(self) -> bool:
        """Check if analysis completed successfully."""
        return self.status == "success"

    def has_results(self) -> bool:
        """Check if analysis has computed results."""
        return (
            self.result is not None
            and self.matches_analyzed > 0
            and self.winrate is not None
        )

    def get_progress_percentage(self) -> float:
        """Get progress as percentage value."""
        return min(100.0, max(0.0, self.progress))

    def get_duration_seconds(self) -> Optional[float]:
        """Get analysis duration in seconds."""
        if not self.started_at:
            return None

        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()


class MatchmakingMetrics(BaseModel):
    """Domain model for analysis metrics with business logic."""

    matches_analyzed: int = Field(..., ge=0)
    player_winrate: float = Field(..., ge=0.0, le=1.0)
    team_avg_winrate: float = Field(..., ge=0.0, le=1.0)
    enemy_avg_winrate: float = Field(..., ge=0.0, le=1.0)
    avg_rank_difference: float = Field(..., ge=0.0)
    fairness_score: float = Field(..., ge=0.0, le=1.0)
    player_puuid: str
    region: str

    def get_fairness_grade(self) -> str:
        """Get letter grade for fairness score."""
        if self.fairness_score >= 0.9:
            return "A+"
        elif self.fairness_score >= 0.8:
            return "A"
        elif self.fairness_score >= 0.7:
            return "B"
        elif self.fairness_score >= 0.6:
            return "C"
        elif self.fairness_score >= 0.5:
            return "D"
        else:
            return "F"

    def is_fair_match(self) -> bool:
        """Check if match is considered fair (score >= 0.7)."""
        return self.fairness_score >= 0.7

    def get_winrate_quality(self) -> str:
        """Get description of winrate quality."""
        if self.player_winrate >= 0.6:
            return "Excellent"
        elif self.player_winrate >= 0.5:
            return "Good"
        elif self.player_winrate >= 0.4:
            return "Average"
        else:
            return "Below Average"


class MatchDataPoint(BaseModel):
    """Single match data point for analysis."""

    match_id: str
    player_win: bool
    team_winrates: List[float]
    enemy_winrates: List[float]
    rank_difference: float

    def get_team_count(self) -> int:
        """Get number of teammates analyzed."""
        return len(self.team_winrates)

    def get_enemy_count(self) -> int:
        """Get number of enemies analyzed."""
        return len(self.enemy_winrates)

    def is_balanced_match(self) -> bool:
        """Check if this match was balanced (small rank difference)."""
        return self.rank_difference <= 200.0