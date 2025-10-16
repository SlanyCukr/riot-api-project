"""Pydantic schemas package for API request/response validation."""

from .players import (
    PlayerCreate,
    PlayerUpdate,
    PlayerResponse,
    PlayerListResponse,
)

from .matches import (
    MatchCreate,
    MatchUpdate,
)
from .response_matches_schema import (
    MatchResponse,
    MatchListResponse,
)

from .participants import (
    MatchParticipantCreate,
    MatchParticipantUpdate,
    MatchParticipantResponse,
    MatchParticipantListResponse,
)

from .ranks import (
    PlayerRankCreate,
    PlayerRankUpdate,
    PlayerRankResponse,
)

from .jobs import (
    JobConfigurationCreate,
    JobConfigurationUpdate,
)
from .response_jobs_schema import (
    JobConfigurationResponse,
    JobExecutionResponse,
    JobExecutionListResponse,
    JobStatusResponse,
    JobTriggerResponse,
)

__all__ = [
    # Player schemas
    "PlayerCreate",
    "PlayerUpdate",
    "PlayerResponse",
    "PlayerListResponse",
    # Match schemas
    "MatchCreate",
    "MatchUpdate",
    "MatchResponse",
    "MatchListResponse",
    # Participant schemas
    "MatchParticipantCreate",
    "MatchParticipantUpdate",
    "MatchParticipantResponse",
    "MatchParticipantListResponse",
    # Rank schemas
    "PlayerRankCreate",
    "PlayerRankUpdate",
    "PlayerRankResponse",
    # Job schemas
    "JobConfigurationCreate",
    "JobConfigurationUpdate",
    "JobConfigurationResponse",
    "JobExecutionResponse",
    "JobExecutionListResponse",
    "JobStatusResponse",
    "JobTriggerResponse",
]
