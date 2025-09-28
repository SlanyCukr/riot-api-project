"""
Pydantic schemas package for API request/response validation.
"""

from .players import (
    PlayerCreate,
    PlayerUpdate,
    PlayerResponse,
    PlayerListResponse,
)

from .matches import (
    MatchCreate,
    MatchUpdate,
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
    PlayerRankListResponse,
)

from .smurf_detection import (
    SmurfDetectionCreate,
    SmurfDetectionUpdate,
    SmurfDetectionResponse,
    SmurfDetectionListResponse,
    SmurfDetectionAnalysis,
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
    "PlayerRankListResponse",

    # Smurf detection schemas
    "SmurfDetectionCreate",
    "SmurfDetectionUpdate",
    "SmurfDetectionResponse",
    "SmurfDetectionListResponse",
    "SmurfDetectionAnalysis",
]