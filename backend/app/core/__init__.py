"""Core infrastructure module.

This module exports core utilities used across features.
Never imports from features - only from external libraries.
"""

from .config import Settings, get_settings, get_global_settings, get_riot_api_key
from .database import get_db, get_session, db_manager
from .exceptions import (
    ServiceException,
    PlayerServiceError,
    DatabaseError,
    ValidationError,
    ExternalServiceError,
)
from .enums import Tier
from .validation import (
    validate_required_fields,
    validate_nested_fields,
    validate_list_items,
    is_empty_or_none,
)
from .models import (
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

__all__ = [
    # Config
    "Settings",
    "get_settings",
    "get_global_settings",
    "get_riot_api_key",
    # Database
    "get_db",
    "get_session",
    "db_manager",
    # Exceptions
    "ServiceException",
    "PlayerServiceError",
    "DatabaseError",
    "ValidationError",
    "ExternalServiceError",
    # Enums
    "Tier",
    # Validation
    "validate_required_fields",
    "validate_nested_fields",
    "validate_list_items",
    "is_empty_or_none",
    # Models
    "Base",
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
