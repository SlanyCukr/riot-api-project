# Riot API Integration Guide

**WHEN TO USE THIS**: Fetching player/match data, handling rate limits, or integrating with Riot Games API.

**CRITICAL**: Always use `RiotDataManager` (not `RiotAPIClient` directly) → [Jump to Usage](#-always-use-riotdatamanager)

---

## 📁 File Structure

```
backend/app/riot_api/
├── client.py           # HTTP client with auth & rate limiting
├── data_manager.py     # ⭐ DATABASE-FIRST data fetching (USE THIS)
├── rate_limiter.py     # Token bucket rate limiting
├── transformers.py     # API response → DB model conversion
├── endpoints.py        # Endpoint definitions & region mapping
├── errors.py           # Custom exception classes
└── models.py           # Pydantic models for API responses
```

---

## ⭐ ALWAYS Use RiotDataManager

**The `RiotDataManager` is your primary interface** - it handles caching, rate limits, and database storage automatically.

### Why Use Data Manager?

| Feature | RiotDataManager | RiotAPIClient |
|---------|-----------------|---------------|
| Database caching | ✅ Automatic | ❌ Manual |
| Rate limit handling | ✅ Returns `None` | ❌ Raises exception |
| Data transformation | ✅ Auto-converts to DB models | ❌ Raw API response |
| Transaction safety | ✅ Built-in | ❌ Manual |

### Basic Usage Pattern

```python
from sqlalchemy.ext.asyncio import AsyncSession
from ..riot_api.data_manager import RiotDataManager
from ..riot_api.client import RiotAPIClient

class PlayerService:
    def __init__(self, db: AsyncSession, riot_data_manager: RiotDataManager):
        self.db = db
        self.data_manager = riot_data_manager

    async def fetch_player(self, game_name: str, tag_line: str, platform: str):
        # Database-first: checks DB, fetches from API if missing
        player = await self.data_manager.get_player_by_riot_id(
            game_name=game_name,
            tag_line=tag_line,
            platform=platform
        )

        if player is None:
            # Rate limited or not found
            return None

        return player
```

---

## 🎯 Quick Reference: Data Manager Methods

### Get Player Data

```python
# By Riot ID (name#tag) - PREFERRED for dev keys
player = await data_manager.get_player_by_riot_id(
    game_name="DangerousDan",
    tag_line="EUW",
    platform="eun1"  # Platform for summoner lookup
)
# Returns: Player model or None

# By PUUID
player = await data_manager.get_player_by_puuid(
    puuid="player-puuid-here"
)
# Returns: Player model or None

# By summoner name (legacy, avoid if possible)
player = await data_manager.get_player_by_summoner_name(
    summoner_name="DangerousDan",
    platform="eun1"
)
# Returns: Player model or None
```

### Get Match Data

```python
# Get match history (returns list of match IDs)
match_ids = await data_manager.get_match_ids(
    puuid="player-puuid",
    count=20,  # Number of matches (default: 20)
    start=0    # Offset (default: 0)
)
# Returns: List[str] or None

# Get match history with full details
matches = await data_manager.get_match_history(
    puuid="player-puuid",
    count=20,
    queue_id=420  # Optional: filter by queue (420=ranked solo)
)
# Returns: List[Match] or None

# Get single match
match = await data_manager.get_match(
    match_id="EUN1_1234567890"
)
# Returns: Match model or None
```

### Get Rank Data

```python
# Get player's current rank
rank = await data_manager.get_player_rank(
    summoner_id="summoner-id-from-player",
    platform="eun1"
)
# Returns: PlayerRank model or None
```

---

## 🔄 Database-First Flow

```
┌─────────────────────────────────────────────────┐
│         RiotDataManager.get_player()            │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
         ┌───────────────┐
         │ Check Database│
         └───────┬───────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
    ┌───────┐      ┌──────────┐
    │ Found │      │ Not Found│
    └───┬───┘      └─────┬────┘
        │                │
        │                ▼
        │      ┌──────────────────┐
        │      │ Fetch from Riot  │
        │      │      API         │
        │      └─────────┬────────┘
        │                │
        │                ▼
        │      ┌──────────────────┐
        │      │  Transform &     │
        │      │  Store in DB     │
        │      └─────────┬────────┘
        │                │
        └────────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │ Return Player │
         └───────────────┘
```

**Key Principles**:
- PostgreSQL is the primary cache
- No TTL - data in DB is considered valid
- API is only called when data is missing
- Rate limit hit = return `None` (no exception)

---

## ⚠️ Rate Limiting

### How It Works

- **Dev keys**: 20 req/sec, 100 req/2min
- **Automatic backoff** on 429 responses
- **Returns `None`** instead of raising exception

### Handle Rate Limits

```python
# ✅ GOOD - Check for None
matches = await data_manager.get_match_history(puuid, count=20)
if matches is None:
    logger.warning("rate_limit_hit", puuid=puuid)
    return []  # Return empty or handle gracefully

# ❌ BAD - Assume success
matches = await data_manager.get_match_history(puuid, count=20)
for match in matches:  # CRASH if matches is None!
    process(match)
```

### Rate Limit Best Practices

1. **Always check for `None` returns**
2. **Log rate limit events** for monitoring
3. **Batch operations** when possible
4. **Use database caching** (automatic with data manager)
5. **Adjust job intervals** if hitting limits frequently

---

## 🔧 Advanced: Using RiotAPIClient (Rare)

**Only use `RiotAPIClient` directly if you need raw API responses without DB storage.**

```python
from ..riot_api.client import RiotAPIClient
from ..riot_api.errors import RateLimitError, NotFoundError

client = RiotAPIClient()

try:
    # Get account by Riot ID
    account_data = await client.get_account(
        game_name="Player",
        tag_line="EUW"
    )

    # Get summoner by PUUID
    summoner_data = await client.get_summoner_by_puuid(
        puuid="...",
        platform="eun1"
    )

    # Get match history
    match_ids = await client.get_match_ids(
        puuid="...",
        region="europe",
        count=20
    )

    # Get match details
    match_data = await client.get_match(
        match_id="EUN1_1234567890",
        region="europe"
    )

except RateLimitError:
    logger.warning("rate_limit_exceeded")
    # Handle rate limit

except NotFoundError:
    logger.warning("resource_not_found")
    # Handle not found
```

---

## 🗺️ Regions and Platforms

### Platform Codes (for summoner/rank data)

```python
PLATFORMS = {
    "eun1",   # Europe Nordic & East
    "euw1",   # Europe West
    "na1",    # North America
    "kr",     # Korea
    "br1",    # Brazil
    "la1",    # Latin America North
    "la2",    # Latin America South
    "oc1",    # Oceania
    "ru",     # Russia
    "tr1",    # Turkey
    "jp1",    # Japan
    "ph2",    # Philippines
    "sg2",    # Singapore
    "th2",    # Thailand
    "tw2",    # Taiwan
    "vn2",    # Vietnam
}
```

### Regional Endpoints (for match data)

```python
REGIONS = {
    "americas",  # NA, BR, LAN, LAS
    "asia",      # KR, JP, SEA
    "europe",    # EUW, EUNE, TR, RU
    "sea",       # PH, SG, TH, TW, VN
}
```

### Platform to Region Mapping

```python
# Automatic conversion in data manager
platform_to_region = {
    "eun1": "europe",
    "euw1": "europe",
    "na1": "americas",
    "br1": "americas",
    "kr": "asia",
    # ... etc
}
```

---

## 🔄 Data Transformation

**The `MatchTransformer` converts API responses to database models.**

### Usage (Automatic in Data Manager)

```python
from ..riot_api.transformers import MatchTransformer

transformer = MatchTransformer()

# Transform match data
transformed = transformer.transform_match_data(raw_api_response)
# Returns: {
#     "match": Match model,
#     "participants": [Participant models]
# }
```

### Manual Transformation (Rare)

```python
# Only needed if you're working with raw API responses
match_data = await client.get_match(match_id, region)
transformed = transformer.transform_match_data(match_data)

match = transformed["match"]
participants = transformed["participants"]

# Store in database
self.db.add(match)
self.db.add_all(participants)
await self.db.commit()
```

---

## 🚨 Error Handling

### Exception Types

```python
from ..riot_api.errors import (
    RiotAPIError,           # Base exception
    RateLimitError,         # 429 - Rate limit exceeded
    AuthenticationError,    # 403 - Invalid API key
    NotFoundError,          # 404 - Resource not found
    ServiceUnavailableError # 503 - Riot API down
)
```

### Handling Errors

```python
from ..riot_api.errors import NotFoundError, RateLimitError

try:
    player = await data_manager.get_player_by_riot_id(
        game_name="Player",
        tag_line="EUW",
        platform="eun1"
    )
except NotFoundError:
    logger.warning("player_not_found", game_name="Player")
    return None
except RateLimitError:
    logger.warning("rate_limit_exceeded")
    return None
```

**NOTE**: `RiotDataManager` catches these internally and returns `None` - you usually don't need try/except.

---

## 🔑 API Key Management

### Dev Key Limitations

- **Expires every 24 hours** (regenerate daily)
- **20 requests/second**
- **100 requests/2 minutes**
- Get new key: https://developer.riotgames.com

### Update API Key

```bash
# In .env file
RIOT_API_KEY=RGAPI-your-new-key-here

# Restart backend
./scripts/dev.sh
```

### 403 Forbidden = Expired Key

```python
# You'll see this in logs:
logger.error("authentication_failed", status_code=403)

# Solution: Regenerate key at developer portal
```

---

## 🧪 Testing with Mocked Riot API

### Mock Data Manager

```python
from unittest.mock import AsyncMock
import pytest

@pytest.fixture
def riot_data_manager_mock():
    """Mock data manager for tests."""
    mock = AsyncMock()

    # Mock player lookup
    mock.get_player_by_riot_id.return_value = Player(
        puuid="test-puuid",
        game_name="TestPlayer",
        tag_line="EUW"
    )

    # Mock match history
    mock.get_match_history.return_value = [
        Match(match_id="EUN1_001", game_duration=1800),
        Match(match_id="EUN1_002", game_duration=2100),
    ]

    return mock
```

### Use in Tests

```python
@pytest.mark.asyncio
async def test_player_service(db, riot_data_manager_mock):
    """Test service with mocked Riot API."""
    service = PlayerService(db, riot_data_manager_mock)

    player = await service.fetch_player("TestPlayer", "EUW", "eun1")

    assert player.puuid == "test-puuid"
    riot_data_manager_mock.get_player_by_riot_id.assert_called_once()
```

---

## 🚨 Common Pitfalls

1. **Don't call `RiotAPIClient` directly from services**
   - ✅ Use `RiotDataManager` for database-first approach
   - ❌ Don't instantiate `RiotAPIClient` in services

2. **Don't forget to check for `None` returns**
   - ✅ `if result is None:` handle gracefully
   - ❌ Assuming API always succeeds

3. **Don't use summoner name when Riot ID is available**
   - ✅ Use `get_player_by_riot_id()` (name#tag)
   - ❌ Using summoner name (not unique, less reliable)

4. **Don't forget region/platform distinction**
   - ✅ Platform for summoner data (eun1, euw1)
   - ✅ Region for match data (europe, americas)
   - ❌ Mixing them up causes 404 errors

5. **Don't store API key in code**
   - ✅ Use environment variable `RIOT_API_KEY`
   - ❌ Hardcoding in source files

---

## 🔗 Related Files

- **`data_manager.py`** - Primary interface (use this!)
- **`client.py`** - Low-level HTTP client
- **`endpoints.py`** - Riot API endpoint definitions
- **`errors.py`** - Custom exception classes
- **`rate_limiter.py`** - Rate limiting implementation
- **`transformers.py`** - Data transformation logic
- **`../services/`** - Services that use data manager

---

## 🔍 Keywords

Riot API, RiotDataManager, RiotAPIClient, rate limiting, API key, database caching, player lookup, match history, region, platform, PUUID, summoner, data transformation, error handling
