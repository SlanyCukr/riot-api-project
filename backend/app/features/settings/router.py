"""Settings API endpoints for managing system configuration."""

from fastapi import APIRouter, HTTPException
import structlog

from .schemas import (
    SettingResponse,
    SettingUpdate,
    SettingTestResponse,
)
from .dependencies import SettingsServiceDep

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/riot_api_key", response_model=SettingResponse)
async def get_riot_api_key(
    settings_service: SettingsServiceDep,
):
    """
    Get the current Riot API key setting.

    Returns the setting with masked value for security.
    The full value is never sent to the frontend.
    """
    try:
        setting = await settings_service.get_setting("riot_api_key")

        if not setting:
            raise HTTPException(
                status_code=404,
                detail="Riot API key setting not found. Using environment variable.",
            )

        return setting

    except Exception as e:
        logger.error("failed_to_get_riot_api_key", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving Riot API key",
        )


@router.put("/riot_api_key", response_model=SettingResponse)
async def update_riot_api_key(
    update: SettingUpdate,
    settings_service: SettingsServiceDep,
):
    """
    Update the Riot API key.

    The new key is validated against the Riot API before being saved.
    If validation fails, the update is rejected.

    **Note**: After updating, you must restart the backend container
    for the changes to take effect:
    ```bash
    docker compose restart backend
    ```
    """
    try:
        # Check if setting exists, create if not
        existing = await settings_service.get_setting("riot_api_key")

        if not existing:
            # Create the setting for the first time
            logger.info("creating_riot_api_key_setting")
            setting = await settings_service.create_or_update_setting(
                key="riot_api_key",
                value=update.value,
                category="riot_api",
                is_sensitive=True,
            )
        else:
            # Update existing setting
            setting = await settings_service.update_setting("riot_api_key", update)

        logger.info(
            "riot_api_key_updated",
            masked_value=setting.masked_value,
        )

        return setting

    except ValueError as e:
        # Validation failed
        logger.warning("riot_api_key_validation_failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error("failed_to_update_riot_api_key", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error updating Riot API key",
        )


@router.post("/riot_api_key/test", response_model=SettingTestResponse)
async def test_riot_api_key(
    update: SettingUpdate,
    settings_service: SettingsServiceDep,
):
    """
    Test a Riot API key without saving it.

    This endpoint validates the provided API key by making a test
    request to the Riot API. The key is not saved to the database.

    Use this to verify a new key before committing the change.
    """
    try:
        test_result = await settings_service.test_riot_api_key(update.value)

        logger.info(
            "riot_api_key_tested",
            success=test_result.success,
            message=test_result.message,
        )

        return test_result

    except Exception as e:
        logger.error("failed_to_test_riot_api_key", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error testing Riot API key",
        )
