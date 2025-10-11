"""
Riot API Backend Application Package.

This package contains the main application logic for the Riot API match history
and smurf detection service.
"""

from .config import get_global_settings
from .database import db_manager, get_db

__version__ = "1.0.0"
__author__ = "Riot API Project Team"

__all__ = [
    "get_global_settings",
    "db_manager",
    "get_db",
]
