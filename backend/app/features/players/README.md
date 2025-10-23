# Players Feature

## Purpose

Manages League of Legends player data, including player search, tracking, rank information, and match history. This feature provides the core player management functionality for the application.

## API Endpoints

### Player Search

- `GET /api/v1/players/search?query={gameName}` - Search for players by game name
- Returns player information including PUUID, summoner data, and current rank

### Player Tracking

- `POST /api/v1/players/{puuid}/track` - Add a player to the tracked players list
- `DELETE /api/v1/players/{puuid}/untrack` - Remove a player from tracking
- `GET /api/v1/players/tracked/list` - Get all tracked players
- `GET /api/v1/players/{puuid}/tracked/status` - Check if a player is being tracked

### Player Details

- `GET /api/v1/players/{puuid}` - Get detailed player information
- `GET /api/v1/players/{puuid}/rank` - Get player's current rank information

## Key Components

### Router (`router.py`)

FastAPI router defining all player-related endpoints. Handles request validation and response formatting.

### Service (`service.py`)

**PlayerService** - Core business logic for player operations:

- Player search via Riot API
- Player data fetching and caching
- Tracked player management
- Rank information retrieval
- Integration with RiotDataManager for data enrichment

### Models (`models.py`, `ranks.py`)

**SQLAlchemy Models:**

- `Player` - Player entity (PUUID, game name, tag line, summoner info, tracking status)
- `Rank` - Player rank data (tier, division, LP, wins, losses, queue type)

### Schemas (`schemas.py`, `ranks_schemas.py`)

**Pydantic Schemas:**

- `PlayerResponse` - API response format for player data
- `PlayerSearchResponse` - Search results with player details
- `RankResponse` - Rank information response
- `TrackPlayerRequest` - Request to track a player

### Dependencies (`dependencies.py`)

- `get_player_service()` - Dependency injection for PlayerService

## Dependencies

### Core Dependencies

- `core.database` - Database session management
- `core.riot_api` - Riot API client and data manager
- `core.enums` - Shared enums (Tier, Platform)
- `core.config` - Application settings

### External Libraries

- SQLAlchemy - ORM for database operations
- Pydantic - Data validation and serialization
- FastAPI - API routing and dependency injection

## Usage Examples

### Adding a New Player Endpoint

```python
from fastapi import APIRouter, Depends
from app.features.players.dependencies import get_player_service
from app.features.players.service import PlayerService
from app.features.players.schemas import PlayerResponse

router = APIRouter()

@router.get("/players/{puuid}/stats", response_model=PlayerResponse)
async def get_player_stats(
    puuid: str,
    player_service: PlayerService = Depends(get_player_service)
):
    return await player_service.get_player_stats(puuid)
```

### Using PlayerService in Another Feature

```python
from app.features.players import PlayerService
from app.features.players.dependencies import get_player_service

# In your router
async def my_endpoint(
    player_service: PlayerService = Depends(get_player_service)
):
    player = await player_service.get_player_by_puuid("player_puuid")
    # Use player data...
```

### Importing Models and Schemas

```python
# Import from feature's public API
from app.features.players import Player, Rank, PlayerResponse, RankResponse

# Or import directly
from app.features.players.models import Player
from app.features.players.schemas import PlayerResponse
```

## Related Features

- **Matches** - Player match history and game data
- **Smurf Detection** - Analyzes player accounts for smurf indicators
- **Matchmaking Analysis** - Evaluates matchmaking fairness for players
- **Jobs** - Background jobs update tracked player data
