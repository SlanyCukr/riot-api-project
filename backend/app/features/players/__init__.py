"""Players feature module."""

# Public API exports
from .router import router as players_router
from .service import PlayerService
from .models import (
    # SQLModel database tables
    Player,
    PlayerRank,
    # SQLModel API schemas
    PlayerBase,
    PlayerRankBase,
    PlayerPublic,
    PlayerPublicWithRanks,
    PlayerRankPublic,
    # SQLModel request schemas
    PlayerSearchRequest,
    PlayerCreate,
    PlayerUpdate,
    PlayerRankUpdate,
    # SQLModel response schemas
    PlayerListResponse,
)

__all__ = [
    # Router
    "players_router",
    # Service
    "PlayerService",
    # Database Models
    "Player",
    "PlayerRank",
    # Base Schemas
    "PlayerBase",
    "PlayerRankBase",
    # Response Schemas
    "PlayerPublic",
    "PlayerPublicWithRanks",
    "PlayerRankPublic",
    # Request Schemas
    "PlayerSearchRequest",
    "PlayerCreate",
    "PlayerUpdate",
    "PlayerRankUpdate",
    # Utility Schemas
    "PlayerListResponse",
]

# NOTE: Imports are intentionally minimal to avoid circular dependencies.
# Import directly from submodules when needed (e.g., from .router import router)
