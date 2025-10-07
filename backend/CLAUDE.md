# Backend Development Guide

This file provides guidance for working with the Python FastAPI backend.

## Backend Structure

- **API Layer**: FastAPI endpoints in `app/api/` (players, matches, detection)
- **Services**: Business logic in `app/services/` (players, matches, detection, stats)
- **Data Models**: SQLAlchemy models in `app/models/` (players, matches, participants, ranks, smurf_detection)
- **Riot API Client**: HTTP client with rate limiting in `app/riot_api/`
- **Algorithms**: Smurf detection algorithms in `app/algorithms/` (win_rate, rank_progression, performance)
- **Background Tasks**: Async task processing in `app/tasks/`
- **Caching**: In-memory caching with TTL support in `app/riot_api/cache.py`

## Core Data Flow

1. Player search by Riot ID or summoner name → PUUID resolution
2. Match history retrieval via Riot API → database storage
3. Participant analysis and encounter tracking
4. Smurf detection using multi-factor algorithms
5. Cached responses for performance optimization

## Key Services

- **PlayerService**: Handles player lookup, PUUID resolution, and basic player data
- **MatchService**: Fetches and processes match history, participant data
- **DetectionService**: Runs smurf detection algorithms and scoring
- **RiotApiClient**: HTTP client with built-in rate limiting and error handling

## Riot API Integration

### Authentication
- Uses `X-Riot-Token` header with API key from environment (`RIOT_API_KEY`)
- **Development keys expire every 24 hours** - regenerate daily at https://developer.riotgames.com
- Rate limiting: 20 requests/second, 100 requests/2 minutes (development keys)
- Automatic backoff and retry on 429 responses
- Platform/Region parameters automatically converted from strings to enums internally

### Key Endpoints Used
- Account v1: Riot ID ↔ PUUID resolution (recommended)
- Summoner v4: Summoner name ↔ PUUID/encrypted ID (**deprecated** - may return 403 with dev keys)
- Match v5: Match history and details
- League v4: Rank and tier information
- Spectator v4: Live game data

**Important**: The `/lol/summoner/v4/summoners/by-name/{summonerName}` endpoint is deprecated. Use Riot ID search instead via `/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}`.

### Regional Routing
- Regional routes (AMERICAS, ASIA, EUROPE, SEA) for Match/Account APIs
- Platform routes (EUN1, EUW1, NA1, etc.) for Summoner/League/Spectator APIs

## Smurf Detection Algorithm

The system uses multiple heuristics:
- Win rate ≥ 65% over 30+ ranked games
- Account level relative to rank
- Rank volatility and climbing speed
- Performance consistency across matches
- KDA ratios and other performance metrics

## Development Guidelines

### Code Style
- Black formatting, isort imports, mypy type checking
- Follow existing patterns and naming conventions

### Testing
- Backend: pytest with async support
- Integration tests for API endpoints
- Mock Riot API responses in tests

### Error Handling
- Use FastAPI's HTTPException for API errors
- Implement proper error logging with structlog
- Handle Riot API rate limits gracefully
- Provide meaningful error messages to frontend

## Performance Considerations

### Caching Strategy
- In-memory TTL cache for Riot API responses
- Configurable cache sizes and TTLs per data type
- Cache Riot API responses with TTL
- Implement cache invalidation for player data updates

### Background Processing
- Async task queue for match data fetching
- Scheduled tasks for data cleanup
- Batch processing for bulk operations
- Rate limiting for Riot API calls

## Database Operations

### Migrations (via Docker)

**Automatic Migration**: Migrations are automatically applied on backend container startup via `entrypoint.sh`. No manual intervention needed.

```bash
# Migrations run automatically on 'docker compose up backend'
# The entrypoint script executes: alembic upgrade head

# Manual migration commands (if needed):
# Create new migration
docker compose exec backend alembic revision --autogenerate -m "description"

# Manually apply migrations (usually not needed)
docker compose exec backend alembic upgrade head

# Rollback migrations
docker compose exec backend alembic downgrade -1

# View current migration version
docker compose exec backend alembic current
```

### Database Schema
- `players`: PUUID-based player identification and metadata
- `matches`: Match details and game information
- `participants`: Individual player performance in matches
- `ranks`: Player rank and tier information
- `smurf_detection`: Smurf detection results and confidence scores

## Testing and Code Quality

```bash
# Run backend tests (inside container)
docker-compose exec backend uv run pytest

# Backend linting and formatting (local - requires uv installed)
cd backend
uv run black .
uv run isort .
uv run flake8 .
uv run mypy .
```

## Environment Configuration

### Required Environment Variables
- `RIOT_API_KEY`: Riot Games API key (required)
- `POSTGRES_PASSWORD`: Database password (required)
- `SECRET_KEY`: Application secret key (required)

### Optional Configuration
- `RIOT_REGION`: Regional routing (default: europe)
- `RIOT_PLATFORM`: Platform routing (default: eun1)
- `DEBUG`: Debug mode (default: false)
- `LOG_LEVEL`: Logging level (default: INFO)