# Matches Feature

## Purpose

Manages League of Legends match data, including match retrieval, storage, and analysis. Provides detailed match information including participants, stats, and game timeline.

## Architecture: Enterprise Pattern with Repository Layer

The matches feature uses **enterprise architecture with repository pattern** following Martin Fowler's patterns:

**Architecture Layers:**

```
Router → Service → Repository → Database
                ↓
          RiotAPIGateway (ACL)
```

**Key Design Patterns:**

- **Repository Pattern**: Abstracts data access with collection-like interface
- **Rich Domain Models**: ORM models contain both data and business logic
- **Data Mapper**: Transformers separate ORM persistence from Pydantic models
- **Anti-Corruption Layer (ACL)**: Gateway isolates Riot API from domain layer
- **Interface Segregation**: Repository interface enables testing and flexibility

## API Endpoints

### Match Data

- `GET /api/v1/matches/{puuid}` - Get match history for a player
- `GET /api/v1/matches/{match_id}/details` - Get detailed information for a specific match
- `GET /api/v1/matches/{puuid}/recent` - Get recent matches with full details

### Match Statistics

- `GET /api/v1/matches/{puuid}/stats` - Get aggregated match statistics
- `GET /api/v1/matches/{puuid}/encounters` - Get encounter history with specific opponents

## Key Components

### Router (`router.py`)

FastAPI router defining all match-related endpoints. Handles match data retrieval and filtering.

### Service (`service.py`)

**MatchService** - Core business logic for match operations:

- Match data fetching from Riot API
- Match history retrieval and pagination
- Match data storage and caching
- Match statistics aggregation
- Opponent encounter tracking

### Models (`models.py`, `participants.py`)

**SQLAlchemy Models:**

- `Match` - Match entity (match ID, queue type, game mode, duration, creation time)
- `MatchParticipant` - Participant data (PUUID, champion, stats, items, runes, performance metrics)

### Schemas (`schemas.py`, `participants_schemas.py`)

**Pydantic Schemas:**

- `MatchResponse` - API response format for match data
- `MatchHistoryResponse` - List of matches with pagination
- `MatchParticipantResponse` - Participant details response
- `MatchStatsResponse` - Aggregated statistics

### Transformers (`transformers.py`)

**MatchDTOTransformer** - Converts Riot API match DTOs to database models:

- Transforms raw API data to structured models
- Enriches match data with additional context
- Handles data normalization and validation

### Dependencies (`dependencies.py`)

- `get_match_service()` - Dependency injection for MatchService

## Dependencies

### Core Dependencies

- `core.database` - Database session management
- `core.riot_api` - Riot API client for match data
- `core.config` - Application settings

### Feature Dependencies

- None (matches feature is independent of other features)

### External Libraries

- SQLAlchemy - ORM for database operations
- Pydantic - Data validation and serialization
- FastAPI - API routing and dependency injection

## Usage Examples

### Fetching Match History

```python
from app.features.matches.dependencies import get_match_service
from app.features.matches.service import MatchService

async def get_player_matches(
    puuid: str,
    match_service: MatchService = Depends(get_match_service)
):
    matches = await match_service.get_match_history(puuid, limit=20)
    return matches
```

### Using Match Models

```python
from app.features.matches.models import Match, MatchParticipant

# Query matches
matches = session.query(Match).filter(
    Match.queue_type == "RANKED_SOLO_5x5"
).all()

# Access participants
for match in matches:
    for participant in match.participants:
        print(f"{participant.summoner_name} played {participant.champion_name}")
```

### Transforming Riot API Data

```python
from app.features.matches.transformers import MatchDTOTransformer

transformer = MatchDTOTransformer()
match_model = transformer.transform(riot_api_match_dto)
session.add(match_model)
await session.commit()
```

## Data Model

### Match

- `match_id` (str, PK) - Riot match ID
- `queue_type` (str) - Queue type (e.g., RANKED_SOLO_5x5)
- `game_mode` (str) - Game mode (e.g., CLASSIC)
- `game_duration` (int) - Match duration in seconds
- `game_creation` (datetime) - Match creation timestamp
- `participants` (relationship) - List of MatchParticipant

### MatchParticipant

- `id` (int, PK) - Auto-increment ID
- `match_id` (str, FK) - Reference to Match
- `puuid` (str) - Player PUUID
- `champion_id` (int) - Champion ID
- `champion_name` (str) - Champion name
- `summoner_name` (str) - Summoner name
- `kills`, `deaths`, `assists` (int) - KDA stats
- `win` (bool) - Victory status
- Additional stats: gold, CS, damage, vision score, etc.

## Related Features

- **Players** - Match history is associated with players
- **Player Analysis** - Analyzes match performance for smurf indicators
- **Matchmaking Analysis** - Uses match data for fairness evaluation
- **Jobs** - Background jobs fetch and update match data
