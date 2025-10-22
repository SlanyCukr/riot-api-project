"""Settings feature module.

This module provides system settings management functionality,
including runtime configuration and Riot API key management.
"""

from .router import router as settings_router
from .service import SettingsService
from .models import SystemSetting
from .schemas import (
    SettingResponse,
    SettingUpdate,
    SettingTestResponse,
    SettingValidationResponse,
)
from .dependencies import get_settings_service, SettingsServiceDep

__all__ = [
    # Router
    "settings_router",
    # Service
    "SettingsService",
    # Models
    "SystemSetting",
    # Schemas
    "SettingResponse",
    "SettingUpdate",
    "SettingTestResponse",
    "SettingValidationResponse",
    # Dependencies
    "get_settings_service",
    "SettingsServiceDep",
]
