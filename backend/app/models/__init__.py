"""
Database models package initialization.
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData

# Create a base class for declarative models
# Use a custom naming convention for constraints and indexes
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
Base = declarative_base(metadata=metadata)

# Import all models here to ensure they are registered with SQLAlchemy
from .players import Player
from .matches import Match
from .participants import MatchParticipant
from .ranks import PlayerRank
from .smurf_detection import SmurfDetection

__all__ = [
    "Base",
    "Player",
    "Match",
    "MatchParticipant",
    "PlayerRank",
    "SmurfDetection",
]