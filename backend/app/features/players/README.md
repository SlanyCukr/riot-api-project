# Players Feature

## Purpose

Manages League of Legends player data, including player search, tracking, rank information, and match history. This feature provides the core player management functionality for the application.

## Architecture: Enterprise Pattern with Repository Layer

The players feature uses **enterprise architecture with repository pattern** following Martin Fowler's patterns:

**Architecture Layers:**

```
Router → Service → Repository → Database
                ↓
          RiotAPIGateway (ACL)
```

**Key Design Patterns:**

- **Repository Pattern**: Abstracts data access with collection-like interface
- **Rich Domain Model**: ORM models contain both data and business logic
- **Data Mapper**: Transformers separate ORM persistence from domain models
- **Anti-Corruption Layer (ACL)**: Gateway isolates Riot API from domain layer
- **Interface Segregation**: Repository interface enables testing and flexibility

## Architecture Decisions

### Domain Model Structure

**Decision**: Keep business logic in ORM models (PlayerORM) rather than separating into distinct Pydantic domain models.

**Rationale**:

- Simpler code with fewer classes to maintain
- Domain logic is co-located with data (better for developer experience)
- SQLAlchemy 2.0 with Mapped types provides good type safety
- Works well in practice for this use case

**Trade-off**: While the enterprise patterns guide suggests separating ORM (persistence) from Pydantic domain models (business logic), we found the combined approach more practical for this project. Both approaches are valid; this is a design choice based on simplicity vs. purity.

**Comparison**:

```
# Our Approach (Current)
PlayerORM (SQLAlchemy + business logic)
    ↓ (transformers convert)
Pydantic API schemas

# Guide's Pure Approach
ORM Models (SQLAlchemy, data only)
    ↓
Pydantic Domain Models (business logic)
    ↓
Pydantic API Schemas (DTOs)
```

### Anti-Corruption Layer (ACL)

**Implementation**: The `RiotAPIGateway` class in `gateway.py` serves as the Anti-Corruption Layer.

**Purpose**:

- Translates Riot API's camelCase naming to our snake_case naming
- Hides multiple API calls from the service layer
- Transforms external DTOs to our domain models
- Prevents external API semantics from leaking into our domain

**Example Transformation**:

```python
# Riot API returns (camelCase, external semantics)
account_dto = {
    "puuid": "...",
    "gameName": "PlayerName",  # camelCase
    "tagLine": "NA1"           # camelCase
}

# Our gateway transforms to (snake_case, our semantics)
player_orm = PlayerORM(
    puuid=account_dto.puuid,
    riot_id=game_name,      # OUR naming
    tag_line=tag_line,      # OUR naming
)
```

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

**Responsibilities:**

- HTTP endpoint definitions with OpenAPI documentation
- Request/response validation via Pydantic schemas
- Dependency injection coordination

### Service (`service.py`)

**PlayerService** - Thin orchestration layer coordinating business operations:

**Responsibilities:**

- Orchestrates repository and Riot API interactions
- Implements high-level business workflows
- Uses RiotAPIGateway (Anti-Corruption Layer) for API calls
- Minimal business logic (most logic in repository or domain models)

**Key Operations:**

- Player search via Riot API
- Player data fetching and caching
- Tracked player management
- Rank information retrieval

### Repository (`repository.py`)

**PlayerRepositoryInterface** - Abstract interface defining data access contract
**SQLAlchemyPlayerRepository** - Concrete implementation for PostgreSQL

**Responsibilities:**

- Data access abstraction (CRUD operations)
- Complex queries (tracked players, stale data, fuzzy search)
- Eager loading optimization (selectinload for relationships)
- Transaction management

**Key Methods:**

- `get_by_puuid()` - Fetch player by PUUID with relationships
- `find_by_riot_id()` - Exact match by Riot ID
- `find_by_summoner_name()` - Fuzzy search by summoner name
- `get_tracked_players()` - Get all tracked players
- `get_players_needing_refresh()` - Find stale data
- `create()` / `save()` - Persistence operations

### Gateway (`gateway.py`)

**RiotAPIGateway** - Anti-Corruption Layer for Riot API integration

**Responsibilities:**

- Translates Riot API DTOs (camelCase) to domain models (snake_case)
- Hides external API structure from the domain layer
- Transforms multiple API calls into single operations
- Prevents external semantics from leaking into business logic

**Key Methods:**

- `fetch_player_profile()` - Fetches player and transforms to PlayerORM
- `fetch_player_ranks()` - Fetches ranked data and transforms to PlayerRankORM list
- `check_ban_status()` - Checks ban status and returns boolean

**Transformation Example:**

```python
# Riot API returns:
{"gameName": "Player", "tagLine": "NA1", "summonerLevel": 45}

# Gateway transforms to:
PlayerORM(riot_id="Player", tag_line="NA1", account_level=45)
```

### ORM Models (`orm_models.py`, `ranks.py`)

**Rich Domain Models** (data + behavior combined):

**PlayerORM** - Player domain model

- Database fields with SQLAlchemy 2.0 Mapped types
- Business logic methods: `track()`, `untrack()`, `mark_for_analysis()`, `update_activity()`
- Domain calculations and validations
- Relationships: ranks, match participants, analysis results

**PlayerRankORM** - Rank domain model

- Rank data (tier, division, LP, wins, losses)
- Business methods: `is_provisional()`, `calculate_mmr_estimate()`, `is_fresh()`
- Queue type handling (RANKED_SOLO_5x5, RANKED_FLEX_SR)

### Pydantic Models (`models.py`)

**Domain Models** (separate from ORM for API layer):

- `Player` - Clean domain representation for API responses
- `Rank` - Rank data transfer object

### Schemas (`schemas.py`, `ranks_schemas.py`)

**Pydantic Schemas for API validation:**

- `PlayerResponse` - API response format for player data
- `PlayerSearchResponse` - Search results with player details
- `RankResponse` - Rank information response
- `TrackPlayerRequest` - Request to track a player

### Transformers (`transformers.py`)

**Data Mapper pattern** - Converts between ORM and Pydantic:

- `PlayerTransformer.to_pydantic()` - ORM → Pydantic domain model
- `PlayerTransformer.to_orm()` - Pydantic → ORM model
- `RankTransformer.to_pydantic()` / `to_orm()` - Rank conversions

**Benefits:**

- Decouples persistence from domain representation
- Enables different views of same data
- Simplifies testing (no SQLAlchemy mocking needed)

### Dependencies (`dependencies.py`)

Dependency injection setup:

- `get_player_repository()` - Creates SQLAlchemyPlayerRepository
- `get_player_service()` - Creates PlayerService with repository and DB session

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
from typing import Annotated
from fastapi import Depends
from app.features.players.service import PlayerService
from app.features.players.dependencies import get_player_service

# In your router
async def my_endpoint(
    player_service: Annotated[PlayerService, Depends(get_player_service)]
):
    player = await player_service.get_player_by_puuid("player_puuid")
    # Use player data...
```

### Using Repository Directly (Advanced)

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.features.players.repository import (
    PlayerRepositoryInterface,
    SQLAlchemyPlayerRepository
)

async def get_player_repository(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> PlayerRepositoryInterface:
    return SQLAlchemyPlayerRepository(db)

# In your router
async def my_endpoint(
    repository: Annotated[PlayerRepositoryInterface, Depends(get_player_repository)]
):
    player_orm = await repository.get_by_puuid("player_puuid")
    # Direct access to ORM model with business methods
    if player_orm:
        player_orm.track()
        await repository.save(player_orm)
```

### Importing Models and Schemas

```python
# Direct module imports (preferred)
from app.features.players.orm_models import PlayerORM  # Rich domain model (SQLAlchemy)
from app.features.players.schemas import PlayerResponse
from app.features.players.repository import PlayerRepositoryInterface
from app.features.players.service import PlayerService
from app.features.players.transformers import PlayerTransformer
```

## Related Features

- **Matches** - Player match history and game data
- **Player Analysis** - Analyzes player accounts for smurf indicators
- **Matchmaking Analysis** - Evaluates matchmaking fairness for players
- **Jobs** - Background jobs update tracked player data
