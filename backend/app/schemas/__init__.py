"""Pydantic schemas package for API request/response validation."""

# NOTE: Most schemas have been moved to feature modules.
# Import them directly from features:
#   from app.features.players.schemas import PlayerResponse
#   from app.features.matches.schemas import MatchResponse
#   etc.

# Only jobs schemas remain here (will be migrated in task 10)
from .jobs import (
    JobConfigurationCreate,
    JobConfigurationUpdate,
    JobConfigurationResponse,
    JobExecutionResponse,
    JobExecutionListResponse,
    JobStatusResponse,
    JobTriggerResponse,
)

__all__ = [
    # Job schemas
    "JobConfigurationCreate",
    "JobConfigurationUpdate",
    "JobConfigurationResponse",
    "JobExecutionResponse",
    "JobExecutionListResponse",
    "JobStatusResponse",
    "JobTriggerResponse",
]
