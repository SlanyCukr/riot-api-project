"""
Riot API Backend Application Package.

This package contains the main application logic for the Riot API match history
and player analysis service.
"""

from .core import get_global_settings, db_manager, get_db
import sys as _sys

_sys.modules.setdefault("app.app", _sys.modules[__name__])

__version__ = "1.0.0"
__author__ = "Riot API Project Team"

__all__ = [
    "get_global_settings",
    "db_manager",
    "get_db",
]
