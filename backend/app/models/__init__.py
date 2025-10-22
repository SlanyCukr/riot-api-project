"""Database models package initialization."""

# Import base class and common types from base module
from .base import (
    Base,
    AutoIncrementPK,
    PrimaryKeyStr,
    PrimaryKeyInt,
    RequiredString,
    OptionalString,
    RequiredInt,
    OptionalInt,
    RequiredBool,
    OptionalBool,
    RequiredDecimal,
    OptionalDecimal,
    RequiredBigInt,
    OptionalBigInt,
    RequiredDateTime,
    OptionalDateTime,
    PUUIDField,
    PUUIDForeignKey,
    MatchIDField,
    MatchIDForeignKey,
)

# NOTE: Models are NOT imported here to avoid circular dependencies.
# Models will be imported by Alembic's env.py for migrations.
# To use models in your code, import them directly from feature modules:
#   from app.features.players.models import Player
#   from app.features.matches.models import Match
#   etc.

__all__ = [
    "Base",
    # Type aliases are exported for convenience
    "AutoIncrementPK",
    "PrimaryKeyStr",
    "PrimaryKeyInt",
    "RequiredString",
    "OptionalString",
    "RequiredInt",
    "OptionalInt",
    "RequiredBool",
    "OptionalBool",
    "RequiredDecimal",
    "OptionalDecimal",
    "RequiredBigInt",
    "OptionalBigInt",
    "RequiredDateTime",
    "OptionalDateTime",
    "PUUIDField",
    "PUUIDForeignKey",
    "MatchIDField",
    "MatchIDForeignKey",
]
