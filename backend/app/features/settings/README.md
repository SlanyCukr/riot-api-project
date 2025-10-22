# Settings Feature

System settings and runtime configuration management.

## Purpose

This feature provides runtime configuration management, allowing administrators to update system settings (like the Riot API key) without redeploying the application.

## API Endpoints

All endpoints are under `/api/v1/settings`:

- `GET /riot_api_key` - Get the current Riot API key (masked for security)
- `PUT /riot_api_key` - Update the Riot API key (validates before saving)
- `POST /riot_api_key/test` - Test an API key without saving it

## Key Components

### Router (`router.py`)
FastAPI routes for settings management with proper error handling.

### Service (`service.py`)
- **SettingsService**: Handles settings CRUD operations
- Validates Riot API keys by making test API calls
- Masks sensitive values in responses

### Models (`models.py`)
- **SystemSetting**: SQLAlchemy model for storing key-value settings
  - Supports categorization (e.g., "riot_api", "jobs", "app")
  - Sensitive flag for automatic value masking
  - Timestamps for audit trail

### Schemas (`schemas.py`)
Pydantic schemas for request/response validation:
- `SettingUpdate`: For updating setting values
- `SettingResponse`: API response with masked sensitive values
- `SettingValidationResponse`: Validation result details
- `SettingTestResponse`: Test result for API key validation

### Dependencies (`dependencies.py`)
- `get_settings_service()`: Dependency injection for SettingsService
- `SettingsServiceDep`: Type alias for dependency injection

## Dependencies

**Core Dependencies:**
- `backend.app.core`: Database, config, and core infrastructure
- `backend.app.core.riot_api`: Riot API client for key validation

**External Dependencies:**
- SQLAlchemy: Database ORM
- Pydantic: Request/response validation
- FastAPI: Web framework
- structlog: Structured logging

## Examples

### Update Riot API Key

```python
PUT /api/v1/settings/riot_api_key
{
  "value": "RGAPI-your-new-key-here"
}
```

Response:
```json
{
  "key": "riot_api_key",
  "masked_value": "****-****-here",
  "category": "riot_api",
  "is_sensitive": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Test API Key

```python
POST /api/v1/settings/riot_api_key/test
{
  "value": "RGAPI-key-to-test"
}
```

Response:
```json
{
  "success": true,
  "message": "API key is valid",
  "details": {
    "validation_details": "Successfully validated with Riot API"
  }
}
```

## Security Notes

- Sensitive settings are **never** returned in full to the frontend
- Values are masked using `****-****-{last_4_chars}` format
- API key validation requires actual Riot API call
- All setting updates are logged with masked values
