# Matches Feature

Match history and statistics feature for League of Legends matches.

## Purpose

Provides match data retrieval and player statistics calculation from stored matches.

## API Endpoints

### GET `/api/v1/matches/player/{puuid}`
Get match history for a player from database.

**Query Parameters:**
- `start` (int, optional): Start index for pagination (default: 0)
- `count` (int, optional): Number of matches to return (default: 20, max: 500)
- `queue` (int, optional): Filter by queue ID (420=Ranked Solo/Duo)
- `start_time` (int, optional): Start timestamp filter
- `end_time` (int, optional): End timestamp filter

**Response:** `MatchListResponse` with paginated matches

### GET `/api/v1/matches/player/{puuid}/stats`
Get player statistics from recent matches.

**Query Parameters:**
- `queue` (int, optional): Filter by queue ID
- `limit` (int, optional): Number of matches to analyze (default: 50, max: 200)

**Response:** `MatchStatsResponse` with aggregated player stats

## Key Components

### Router (`router.py`)
FastAPI endpoints for match data retrieval.

### Service (`service.py`)
Business logic for:
- Fetching matches from database
- Calculating player statistics
- Fetching and storing matches from Riot API (used by background jobs)
- Managing match participants

### Models
- `models.py`: `Match` - Match metadata and game information
- `participants.py`: `MatchParticipant` - Individual player performance in matches

### Schemas
- `schemas.py`: Match request/response schemas
- `participants_schemas.py`: Participant schemas
- `transformers.py`: DTO transformation utilities

### Dependencies (`dependencies.py`)
- `get_match_service()`: Factory for MatchService instances
- `MatchServiceDep`: Type alias for dependency injection

## Dependencies

### Internal
- `app.core.database`: Database session management
- `app.core.riot_api`: Riot API client and transformers
- `app.models.players`: Player model (not yet migrated)
- `app.utils.statistics`: Statistical utility functions

### External
- SQLAlchemy 2.0+: Database ORM
- Pydantic v2: Data validation
- FastAPI: API framework

## Usage Example

```python
from app.features.matches import MatchService, get_match_service

# In a FastAPI endpoint
@router.get("/custom-endpoint")
async def my_endpoint(match_service: MatchServiceDep):
    matches = await match_service.get_player_matches(
        puuid="player-uuid",
        count=20,
        queue=420
    )
    return matches
```

## Notes

- All match data is served from database only (no direct Riot API calls from endpoints)
- Background jobs handle fetching new matches from Riot API
- Supports pagination for large match histories
- Calculates statistics (KDA, win rate, CS, vision score) from match participants
