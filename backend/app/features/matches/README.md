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
                ↓
           Data Mapper (Transformers)
```

**Key Design Patterns:**

- **Repository Pattern**: Abstracts data access with collection-like interface
- **Rich Domain Models**: ORM models contain both data and business logic
- **Data Mapper**: Transformers separate ORM persistence from Pydantic models
- **Anti-Corruption Layer (ACL)**: Gateway isolates Riot API from domain layer
- **Interface Segregation**: Repository interface enables testing and flexibility
- **Dependency Injection**: Clean separation of concerns and testability

**Enterprise Architecture Benefits:**

- **Testability**: Repository interfaces enable easy mocking
- **Maintainability**: Clear separation of responsibilities
- **Flexibility**: Easy to swap implementations (e.g., different databases)
- **Domain Protection**: ACL prevents external API contamination
- **Rich Behavior**: Domain models contain business logic, not just data

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

FastAPI router defining all match-related endpoints. Handles match data retrieval and filtering with thin controllers that delegate to services.

### Service (`service.py`)

**MatchService** - Business orchestration layer (thin service pattern):

- Orchestrates repository and gateway operations
- Coordinates complex workflows (match fetching + storage)
- Handles transaction management
- Delegates database operations to repository
- Delegates external API calls to gateway

### Repository (`repository.py`)

**Repository Pattern Implementation:**

- `MatchRepositoryInterface` - Abstract interface for testability
- `SQLAlchemyMatchRepository` - Concrete implementation
- `MatchParticipantRepositoryInterface` - Participant repository interface
- `SQLAlchemyMatchParticipantRepository` - Participant repository implementation

Provides collection-like interface for domain objects while hiding database complexity.

### Gateway (`gateway.py`)

**RiotMatchGateway** - Anti-Corruption Layer (ACL):

- Isolates domain from Riot API semantics
- Transforms Riot DTOs to domain models
- Handles API-specific error translation
- Manages rate limiting and retry logic
- Provides clean domain interface

### ORM Models (`orm_models.py`, `participants_orm.py`)

**Rich Domain Models (SQLAlchemy 2.0):**

- `MatchORM` - Match entity with business logic methods
- `MatchParticipantORM` - Participant entity with domain behavior
- Rich methods: `is_ranked()`, `get_duration_formatted()`, `get_win_rate()`, etc.
- Type-safe with SQLAlchemy 2.0 Mapped types
- Proper indexing and relationship definitions

### Schemas (`schemas.py`, `participants_schemas.py`)

**Pydantic Schemas (v2):**

- `MatchResponse` - API response format for match data
- `MatchListResponse` - List of matches with pagination
- `MatchParticipantResponse` - Participant details response
- `MatchStatsResponse` - Aggregated statistics
- `ConfigDict` with `from_attributes=True` for ORM compatibility

### Transformers (`transformers.py`, `match_transformers.py`)

**Data Mapper Pattern:**

- `MatchTransformer` - Converts between ORM models and Pydantic schemas
- `match_orm_to_response()` - ORM to API response transformation
- `match_participant_orm_to_response()` - Participant transformation
- Separates persistence concerns from domain logic

### Dependencies (`dependencies.py`)

**Dependency Injection Factory:**

- `get_match_service()` - Provides MatchService with injected dependencies
- `get_match_repository()` - Provides repository instance
- `get_riot_match_gateway()` - Provides gateway instance
- Clean dependency graph for testability

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

### Using the Repository Pattern

```python
from app.features.matches.repository import MatchRepositoryInterface, SQLAlchemyMatchRepository
from sqlalchemy.ext.asyncio import AsyncSession

async def get_player_matches_enterprise(
    puuid: str,
    db: AsyncSession
):
    """Enterprise pattern usage with repository."""
    repository = SQLAlchemyMatchRepository(db)

    # Repository provides collection-like interface
    matches = await repository.find_by_player(
        puuid=puuid,
        limit=20,
        queue_id=420  # Ranked Solo/Duo
    )

    return matches
```

### Using the Service Layer

```python
from app.features.matches.dependencies import get_match_service
from app.features.matches.service import MatchService

async def get_player_matches_with_service(
    puuid: str,
    match_service: MatchService = Depends(get_match_service)
):
    """Service layer orchestrates repository and gateway."""
    matches = await match_service.get_match_history(puuid, limit=20)
    return matches
```

### Using Rich Domain Models

```python
from app.features.matches.orm_models import MatchORM, MatchParticipantORM

# Query matches using async/await pattern
async def analyze_matches(db: AsyncSession):
    result = await db.execute(
        select(MatchORM).where(MatchORM.queue_id == 420)
    )
    matches = result.scalars().all()

    # Rich domain models have business logic methods
    for match in matches:
        print(f"Match {match.match_id}: {match.get_duration_formatted()}")
        print(f"Game type: {match.get_game_type_name()}")
        print(f"Is ranked: {match.is_ranked()}")

        # Participants are also rich domain models
        for participant in match.participants:
            print(f"  {participant.summoner_name}: {participant.champion_name}")
            print(f"  KDA: {participant.get_kda_ratio():.2f}")
            print(f"  Win rate: {participant.get_win_rate():.1%}")
```

### Using the Gateway (Anti-Corruption Layer)

```python
from app.features.matches.gateway import RiotMatchGateway
from app.core.riot_api.client import RiotAPIClient

async def fetch_match_from_riot():
    """Gateway isolates domain from Riot API specifics."""
    riot_client = RiotAPIClient()
    gateway = RiotMatchGateway(riot_client)

    # Gateway handles API translation and error handling
    match_orm = await gateway.fetch_match_by_id("NA1_123456789")
    return match_orm
```

### Using Data Mapper (Transformers)

```python
from app.features.matches.transformers import match_orm_to_response
from app.features.matches.orm_models import MatchORM

async def api_response_example(match_orm: MatchORM):
    """Data mapper separates persistence from presentation."""
    # Convert ORM model to API response schema
    response = match_orm_to_response(match_orm)
    return response

# For batch transformations
from app.features.matches.transformers import MatchTransformer

transformer = MatchTransformer()
responses = transformer.transform_matches_to_responses(match_orm_list)
```

### Dependency Injection in FastAPI Endpoints

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.features.matches.dependencies import get_match_service
from app.features.matches.service import MatchService

router = APIRouter()

@router.get("/players/{puuid}/matches")
async def get_player_matches(
    puuid: str,
    limit: int = 20,
    match_service: MatchService = Depends(get_match_service)
):
    """Clean dependency injection with enterprise patterns."""
    matches = await match_service.get_match_history(puuid, limit=limit)
    return {"matches": matches, "count": len(matches)}
```

## Data Model

### MatchORM (Rich Domain Model)

**Database Fields:**

- `match_id` (str, PK) - Riot match ID
- `platform_id` (str) - Riot platform (NA1, EUW1, etc.)
- `queue_id` (int) - Queue type ID (420=Ranked Solo, 440=Ranked Flex)
- `game_mode` (str) - Game mode (CLASSIC, ARAM, etc.)
- `game_type` (str) - Game type (MATCHED_GAME, TUTORIAL)
- `game_duration` (int) - Match duration in seconds
- `game_creation` (datetime) - Match creation timestamp
- `game_version` (str) - Patch version (e.g., "13.24.123")
- `is_processed` (bool) - Processing status flag
- `processing_error` (str) - Error message if processing failed

**Rich Domain Methods:**

- `is_ranked()` - Check if match is ranked queue
- `get_game_type_name()` - Get human-readable game type
- `get_duration_formatted()` - Get duration as MM:SS string
- `get_season_number()` - Extract season from game version
- `is_recent(days=30)` - Check if match is within recent period

**Relationships:**

- `participants` - List of MatchParticipantORM (one-to-many)

### MatchParticipantORM (Rich Domain Model)

**Database Fields:**

- `id` (int, PK) - Auto-increment ID
- `match_id` (str, FK) - Reference to MatchORM
- `puuid` (str) - Player PUUID
- `champion_id` (int) - Champion ID
- `champion_name` (str) - Champion name
- `summoner_name` (str) - Summoner name
- `team_id` (int) - Team identifier (100=Blue, 200=Red)
- `win` (bool) - Victory status
- `kills`, `deaths`, `assists` (int) - KDA stats
- `gold_earned` (int) - Total gold earned
- `total_minions_killed` (int) - CS count
- `vision_score` (int) - Vision control score
- `damage_dealt` (int) - Total damage dealt to champions
- `damage_taken` (int) - Total damage taken
- `wards_placed`, `wards_killed` (int) - Vision control stats
- `item_0` through `item_6` (int) - Item IDs
- `spell_1_id`, `spell_2_id` (int) - Summoner spell IDs

**Rich Domain Methods:**

- `get_kda_ratio()` - Calculate K/D/A ratio
- `get_kill_participation()` - Calculate kill participation percentage
- `get_cs_per_minute()` - Calculate CS per minute
- `get_gold_per_minute()` - Calculate gold per minute
- `get_win_rate()` - Calculate win rate (requires multiple matches)
- `has_trinket()` - Check if player equipped trinket
- `get_item_build()` - Get formatted item build string

**Relationships:**

- `match` - Reference to MatchORM (many-to-one)

**Indexes for Performance:**

- Primary key on `id`
- Foreign key index on `match_id`
- Composite index on `(puuid, match_id)` for player match lookups
- Index on `champion_id` for champion statistics

## Enterprise Architecture Migration

### Migration Overview

The matches feature has been migrated from standard patterns to enterprise architecture:

**Before (Standard Pattern):**

- Service contained both business logic and data access
- Direct database queries mixed with business rules
- Tight coupling to Riot API structures
- Anemic domain models (just data containers)

**After (Enterprise Pattern):**

- Repository pattern abstracts data access
- Rich domain models contain business logic
- Gateway (ACL) isolates external API
- Clean separation of concerns
- Testable and maintainable code

### Testing Strategy

**Unit Testing:**

- Mock repository interfaces for service layer tests
- Test rich domain model methods independently
- Test gateway with mock Riot API client
- Test data mapper transformations

**Integration Testing:**

- Test repository with test database
- Test service orchestration with real dependencies
- Test API endpoints with full dependency chain

**Test Example:**

```python
import pytest
from unittest.mock import AsyncMock, Mock
from app.features.matches.service import MatchService
from app.features.matches.repository import MatchRepositoryInterface

@pytest.mark.asyncio
async def test_match_service_with_mocked_repo():
    """Test service layer with repository mocking."""
    # Arrange
    mock_repo = AsyncMock(spec=MatchRepositoryInterface)
    mock_repo.find_by_player.return_value = []

    service = MatchService(repository=mock_repo, gateway=Mock())

    # Act
    matches = await service.get_match_history("puuid", limit=10)

    # Assert
    assert matches == []
    mock_repo.find_by_player.assert_called_once_with("puuid", 10, None, None, None)
```

## Related Features

- **Players** - Match history is associated with players
- **Player Analysis** - Analyzes match performance for smurf indicators
- **Matchmaking Analysis** - Uses match data for fairness evaluation
- **Jobs** - Background jobs fetch and update match data

## Performance Considerations

**Database Indexing:**

- Composite indexes on common query patterns
- Foreign key indexes for relationship performance
- Partitioning strategies for large datasets

**Caching Strategy:**

- Recent matches cached in memory
- Aggregated statistics cached with TTL
- Repository pattern enables caching layer insertion

**Async Operations:**

- All database operations use async/await
- Riot API calls are non-blocking
- Concurrent processing of match data
