# Settings Feature

## Purpose

Manages system-wide configuration settings for the application. Provides a persistent key-value store for runtime configuration that can be modified without requiring application restarts or environment variable changes.

## API Endpoints

### Settings Management

- `GET /api/v1/settings/` - List all system settings
- `GET /api/v1/settings/{key}` - Get a specific setting by key
- `POST /api/v1/settings/` - Create a new setting
- `PUT /api/v1/settings/{key}` - Update an existing setting
- `DELETE /api/v1/settings/{key}` - Delete a setting

### Riot API Key Management

- `GET /api/v1/settings/riot_api_key` - Get the current Riot API key (masked for security)
- `PUT /api/v1/settings/riot_api_key` - Update the Riot API key (validates before saving)
- `POST /api/v1/settings/riot_api_key/test` - Test an API key without saving it

### Bulk Operations

- `GET /api/v1/settings/category/{category}` - Get all settings in a category
- `PUT /api/v1/settings/bulk` - Update multiple settings at once

## Key Components

### Router (`router.py`)

FastAPI router defining settings management endpoints. Handles CRUD operations for system settings with proper error handling.

### Service (`service.py`)

**SettingsService** - Core business logic for settings operations:

- Setting retrieval and caching
- Setting validation and updates
- Category-based organization
- Default value management
- Riot API key validation via test API calls
- Sensitive value masking

### Models (`models.py`)

**SQLAlchemy Models:**

- `SystemSetting` - Setting entity (key, value, category, description, data type, sensitive flag)

### Schemas (`schemas.py`)

**Pydantic Schemas:**

- `SystemSettingResponse` - API response format for settings
- `SystemSettingCreate` - Create setting request
- `SystemSettingUpdate` - Update setting request
- `BulkSettingsUpdate` - Bulk update request
- `SettingValidationResponse` - Validation result details
- `SettingTestResponse` - Test result for API key validation

### Dependencies (`dependencies.py`)

- `get_settings_service()` - Dependency injection for SettingsService

## Dependencies

### Core Dependencies

- `core.database` - Database session management
- `core.config` - Application settings (environment-based defaults)
- `core.riot_api` - Riot API client for key validation

### Feature Dependencies

- None (settings feature is independent)

### External Libraries

- SQLAlchemy - ORM for database operations
- Pydantic - Data validation and serialization
- FastAPI - API routing and dependency injection

## Setting Categories

Settings are organized into logical categories:

### 1. Riot API (`riot_api`)

- Riot API key configuration
- Rate limit configurations
- API request timeouts
- Regional endpoints

### 2. Job Configuration (`jobs`)

- Job schedules and intervals
- Job execution timeouts
- Job retry policies

### 3. Analysis Settings (`analysis`)

- Player analysis thresholds
- Matchmaking analysis weights
- Statistical calculation parameters

### 4. System Settings (`app`)

- Database connection pool sizes
- Logging levels
- Cache TTL values

### 5. Feature Flags (`feature_flags`)

- Enable/disable specific features
- Beta feature toggles
- Experimental functionality

## Usage Examples

### Retrieving a Setting

```python
from app.features.settings.dependencies import get_settings_service

async def get_setting_example(
    settings_service = Depends(get_settings_service)
):
    setting = await settings_service.get_setting("player_analysis_threshold")
    print(f"Value: {setting.value}")
    print(f"Type: {setting.data_type}")
```

### Creating a Setting

```python
from app.features.settings.schemas import SystemSettingCreate

async def create_setting_example(
    settings_service = Depends(get_settings_service)
):
    new_setting = SystemSettingCreate(
        key="custom_feature_enabled",
        value="true",
        category="feature_flags",
        description="Enable custom feature",
        data_type="boolean"
    )

    created = await settings_service.create_setting(new_setting)
    return created
```

### Updating Riot API Key

```python
from app.features.settings.schemas import SystemSettingUpdate

async def update_api_key(
    settings_service = Depends(get_settings_service)
):
    # Update validates the key before saving
    update = SystemSettingUpdate(value="RGAPI-your-new-key-here")

    updated = await settings_service.update_setting("riot_api_key", update)
    return updated  # Returns masked value
```

### Testing API Key

```python
async def test_api_key(
    settings_service = Depends(get_settings_service)
):
    result = await settings_service.test_riot_api_key("RGAPI-key-to-test")

    if result.success:
        print("API key is valid!")
    else:
        print(f"Invalid key: {result.message}")
```

### Bulk Update

```python
async def bulk_update_example(
    settings_service = Depends(get_settings_service)
):
    updates = {
        "job_interval_player_update": "20",
        "job_interval_match_fetch": "35",
        "player_analysis_enabled": "true"
    }

    results = await settings_service.bulk_update(updates)
    print(f"Updated {len(results)} settings")
```

## Data Model

### SystemSetting

- `id` (int, PK) - Auto-increment ID
- `key` (str, unique) - Setting identifier (e.g., "riot_api_key")
- `value` (str) - Setting value (stored as string, cast to appropriate type)
- `category` (str) - Category for organization (e.g., "riot_api", "jobs")
- `description` (str, optional) - Human-readable description
- `data_type` (str) - Data type hint ("string", "int", "float", "boolean", "json")
- `is_sensitive` (bool) - Whether value should be masked in responses
- `created_at` (datetime) - Creation timestamp
- `updated_at` (datetime) - Last modification timestamp

## Supported Data Types

Settings support automatic type conversion:

### String

```python
{"key": "api_endpoint", "value": "https://api.example.com", "data_type": "string"}
```

### Integer

```python
{"key": "max_retries", "value": "3", "data_type": "int"}
```

### Float

```python
{"key": "threshold", "value": "0.75", "data_type": "float"}
```

### Boolean

```python
{"key": "feature_enabled", "value": "true", "data_type": "boolean"}
```

### JSON

```python
{"key": "config_object", "value": '{"a": 1, "b": 2}', "data_type": "json"}
```

## Security Features

### Sensitive Value Masking

- Sensitive settings (like `riot_api_key`) are **never** returned in full
- Values are masked using `****-****-{last_4_chars}` format
- API responses automatically mask sensitive values
- All setting updates are logged with masked values

### API Key Validation

- Riot API keys are validated before being saved
- Validation makes actual Riot API call to verify the key works
- Test endpoint allows validation without saving
- Invalid keys are rejected with detailed error messages

## Best Practices

### Naming Conventions

- Use lowercase with underscores: `job_interval_player_update`
- Prefix by category: `riot_api_timeout`, `player_analysis_threshold`
- Be descriptive: `enable_experimental_feature_x` not `exp_feat_x`

### Default Values

Always provide sensible defaults in code to handle missing settings:

```python
async def get_with_default(key: str, default: str):
    try:
        setting = await settings_service.get_setting(key)
        return setting.value
    except NotFoundError:
        return default
```

### Validation

Validate setting values before updates:

```python
def validate_threshold(value: str) -> bool:
    try:
        float_value = float(value)
        return 0.0 <= float_value <= 1.0
    except ValueError:
        return False
```

## Related Features

- **Jobs** - Jobs read configuration from settings
- **Player Analysis** - Detection thresholds configurable via settings
- **Matchmaking Analysis** - Analysis weights configurable via settings
- All features can use settings for runtime configuration

## Future Enhancements

- Setting validation rules and constraints
- Setting change history and audit log
- Setting templates for common configurations
- Export/import settings for environment migration
- Real-time setting updates without service restart
