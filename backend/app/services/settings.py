"""Service for managing system settings."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import structlog

from ..models.settings import SystemSetting
from ..schemas.settings import (
    SettingResponse,
    SettingUpdate,
    SettingValidationResponse,
    SettingTestResponse,
)
from ..riot_api.client import RiotAPIClient
from ..riot_api.constants import Platform, Region
from ..riot_api.errors import AuthenticationError, ForbiddenError, NotFoundError

logger = structlog.get_logger(__name__)


class SettingsService:
    """Service for handling system settings operations."""

    def __init__(self, db: AsyncSession):
        """Initialize settings service."""
        self.db = db

    async def get_setting(self, key: str) -> Optional[SettingResponse]:
        """Get a setting by key."""
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        result = await self.db.execute(stmt)
        setting = result.scalar_one_or_none()

        if not setting:
            logger.info("setting_not_found", key=key)
            return None

        # Create response with masked value (never send full value to frontend)
        response = SettingResponse(
            key=setting.key,
            masked_value=setting.mask_value(),
            category=setting.category,
            is_sensitive=setting.is_sensitive,
            created_at=setting.created_at,
            updated_at=setting.updated_at,
        )

        logger.info("setting_retrieved", key=key, category=setting.category)
        return response

    async def update_setting(self, key: str, update: SettingUpdate) -> SettingResponse:
        """Update a setting value."""
        # Get existing setting
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        result = await self.db.execute(stmt)
        setting = result.scalar_one_or_none()

        if not setting:
            raise ValueError(f"Setting '{key}' not found")

        # Validate the new value before saving
        if key == "riot_api_key":
            validation = await self.validate_riot_api_key(update.value)
            if not validation.valid:
                logger.warning(
                    "setting_validation_failed",
                    key=key,
                    message=validation.message,
                )
                raise ValueError(f"Invalid Riot API key: {validation.message}")

        # Update the value
        old_value_masked = setting.mask_value()
        setting.value = update.value

        await self.db.commit()
        await self.db.refresh(setting)

        logger.info(
            "setting_updated",
            key=key,
            old_value=old_value_masked,
            new_value=setting.mask_value(),
        )

        # Return updated setting (masked value only for security)
        return SettingResponse(
            key=setting.key,
            masked_value=setting.mask_value(),
            category=setting.category,
            is_sensitive=setting.is_sensitive,
            created_at=setting.created_at,
            updated_at=setting.updated_at,
        )

    async def create_or_update_setting(
        self, key: str, value: str, category: str, is_sensitive: bool = False
    ) -> SettingResponse:
        """Create or update a setting."""
        # Check if setting exists
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        result = await self.db.execute(stmt)
        setting = result.scalar_one_or_none()

        if setting:
            # Update existing
            setting.value = value
            setting.category = category
            setting.is_sensitive = is_sensitive
            logger.info("setting_updated", key=key)
        else:
            # Create new
            setting = SystemSetting(
                key=key,
                value=value,
                category=category,
                is_sensitive=is_sensitive,
            )
            self.db.add(setting)
            logger.info("setting_created", key=key, category=category)

        await self.db.commit()
        await self.db.refresh(setting)

        return SettingResponse(
            key=setting.key,
            masked_value=setting.mask_value(),
            category=setting.category,
            is_sensitive=setting.is_sensitive,
            created_at=setting.created_at,
            updated_at=setting.updated_at,
        )

    async def validate_riot_api_key(self, api_key: str) -> SettingValidationResponse:
        """Validate a Riot API key by making a test API call."""
        if not api_key or len(api_key) < 10:
            return SettingValidationResponse(
                valid=False,
                message="API key is too short",
                details="Riot API keys should start with 'RGAPI-'",
            )

        if not api_key.startswith("RGAPI-"):
            return SettingValidationResponse(
                valid=False,
                message="Invalid API key format",
                details="Riot API keys must start with 'RGAPI-'",
            )

        # Test the API key with a simple request
        try:
            client = RiotAPIClient(
                api_key=api_key,
                region=Region.EUROPE,
                platform=Platform.EUN1,
            )
            await client.start_session()

            try:
                # Make a test request to verify the API key works
                # Use account endpoint - it's more reliable and works with all API key types
                # We use a well-known account - we expect 200 which means the key is valid
                test_url = client.endpoints.account_by_riot_id("Faker", "KR1")
                logger.info("riot_api_key_validation_attempt", test_url=test_url)

                response = await client._make_request(
                    test_url,
                    method="GET",
                    retry_on_failure=False,
                )

                # If we get here without exception, the API key is valid
                logger.info(
                    "riot_api_key_validated",
                    status="success",
                    response_type=type(response).__name__,
                )
                return SettingValidationResponse(
                    valid=True,
                    message="API key is valid",
                    details="Successfully validated with Riot API",
                )

            except AuthenticationError as e:
                # 401 - Invalid API key
                logger.warning(
                    "riot_api_key_validation_failed", error="401", details=str(e)
                )
                return SettingValidationResponse(
                    valid=False,
                    message="API key is invalid",
                    details="Received 401 Unauthorized from Riot API. The API key format is correct but the key itself is not recognized.",
                )
            except ForbiddenError as e:
                # 403 - API key expired or forbidden
                logger.warning(
                    "riot_api_key_validation_failed", error="403", details=str(e)
                )
                return SettingValidationResponse(
                    valid=False,
                    message="API key has expired",
                    details="Received 403 Forbidden from Riot API. Development keys expire every 24 hours - please generate a new key at developer.riotgames.com",
                )
            except NotFoundError:
                # 404 - Account not found. Key is still valid, but account doesn't exist
                # This shouldn't happen with Faker account, but treat as valid anyway
                logger.info(
                    "riot_api_key_validated",
                    status="success",
                    note="404_account_not_found",
                )
                return SettingValidationResponse(
                    valid=True,
                    message="API key is valid",
                    details="Successfully validated with Riot API (test account not found, but authentication succeeded)",
                )
            finally:
                await client.close()

        except Exception as e:
            logger.error(
                "riot_api_key_validation_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return SettingValidationResponse(
                valid=False,
                message="Failed to validate API key",
                details=f"Unexpected error during validation: {str(e)}",
            )

    async def test_riot_api_key(self, api_key: str) -> SettingTestResponse:
        """Test a Riot API key without saving it."""
        validation = await self.validate_riot_api_key(api_key)

        return SettingTestResponse(
            success=validation.valid,
            message=validation.message,
            details={"validation_details": validation.details}
            if validation.details
            else None,
        )
