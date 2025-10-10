"""Database models package initialization."""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData

# Create a base class for declarative models
# Use a custom naming convention for constraints and indexes
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)
Base = declarative_base(metadata=metadata)

# Import all models here to ensure they are registered with SQLAlchemy
# fmt: off (noqa: E402)
from .players import Player  # noqa: E402
from .matches import Match  # noqa: E402
from .participants import MatchParticipant  # noqa: E402
from .ranks import PlayerRank  # noqa: E402
from .smurf_detection import SmurfDetection  # noqa: E402
from .data_tracking import DataTracking, APIRequestQueue, RateLimitLog  # noqa: E402

# fmt: on

__all__ = [
    "Base",
    "Player",
    "Match",
    "MatchParticipant",
    "PlayerRank",
    "SmurfDetection",
    "DataTracking",
    "APIRequestQueue",
    "RateLimitLog",
]
