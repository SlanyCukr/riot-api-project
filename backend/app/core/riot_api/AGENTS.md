# Tech Stack

- httpx for async HTTP requests
- Token bucket rate limiting
- Database-first caching strategy
- Pydantic models for API responses

# Project Structure

- `client.py` - HTTP client with auth and rate limiting
- `data_manager.py` - Primary interface (database-first)
- `rate_limiter.py` - Token bucket implementation
- `transformers.py` - API response to DB model conversion
- `endpoints.py` - Riot API endpoint definitions
- `constants.py` - Region, platform, and queue enums

# Commands

- Check for None returns (rate limits)
- Update RIOT_API_KEY in .env for 403 errors

# Code Style

- Always use RiotDataManager (not RiotAPIClient)
- Handle rate limits with None checks
- Use enum constants for regions/platforms
- Transform data to DB models automatically

# Do Not

- Don't call RiotAPIClient directly from services
- Don't assume API calls always succeed
- Don't mix region and platform codes
- Don't store API key in code
