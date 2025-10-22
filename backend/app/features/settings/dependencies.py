"""Dependency injection for settings feature."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_db
from .service import SettingsService


async def get_settings_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingsService:
    """
    Get settings service instance.

    :param db: Database session
    :returns: SettingsService instance
    """
    return SettingsService(db)


# Type alias for dependency injection
SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]
