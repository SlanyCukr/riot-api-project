"""Player analysis feature module with enterprise architecture.

This module provides player smurf detection using multi-factor analysis
with repository pattern, rich domain models, and data transformers.
"""

# Import directly from submodules to avoid circular dependencies
from .router import router as player_analysis_router
from .service import PlayerAnalysisService
from .orm_models import PlayerAnalysisORM
from .repository import (
    PlayerAnalysisRepositoryInterface,
    SQLAlchemyPlayerAnalysisRepository,
)
from .transformers import PlayerAnalysisTransformer
from .schemas import DetectionResponse, DetectionFactor

__all__ = [
    "player_analysis_router",
    "PlayerAnalysisService",
    "PlayerAnalysisORM",
    "PlayerAnalysisRepositoryInterface",
    "SQLAlchemyPlayerAnalysisRepository",
    "PlayerAnalysisTransformer",
    "DetectionResponse",
    "DetectionFactor",
]
