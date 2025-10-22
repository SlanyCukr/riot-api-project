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
from .logging import setup_logging, get_logger
from .enums import Tier

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
    # Logging
    "setup_logging",
    "get_logger",
    # Enums
    "Tier",
]
