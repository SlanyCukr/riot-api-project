# API Endpoints Guide

**WHEN TO USE THIS**: Adding/modifying API endpoints, implementing FastAPI patterns, or handling HTTP requests.

**QUICK START**: Adding endpoint? → [Jump to Quick Recipe](#quick-recipe-add-an-endpoint)

---

## 📍 Available Endpoints

### Players API (`app/api/players.py`)
```
GET  /api/v1/players/search              # Search by Riot ID or summoner name
GET  /api/v1/players/{puuid}             # Get player by PUUID
GET  /api/v1/players/{puuid}/recent      # Get recent match IDs
GET  /api/v1/players/                    # List all players (paginated)
POST /api/v1/players/{puuid}/track       # Mark player as tracked
DELETE /api/v1/players/{puuid}/track     # Untrack player
GET  /api/v1/players/{puuid}/tracking-status  # Check tracking status
GET  /api/v1/players/tracked/list        # List all tracked players
GET  /api/v1/players/{puuid}/rank        # Get player's current rank
```

### Matches API (`app/api/matches.py`)
```
GET  /api/v1/matches/player/{puuid}      # Get match history for player
GET  /api/v1/matches/{match_id}          # Get detailed match info
GET  /api/v1/matches/player/{puuid}/stats  # Aggregated statistics
GET  /api/v1/matches/player/{puuid}/encounters  # Recurring encounters
POST /api/v1/matches/search              # Advanced match search
GET  /api/v1/matches/{match_id}/participants  # All participants
```

### Detection API (`app/api/detection.py`)
```
POST /api/v1/detection/analyze           # Run smurf detection
GET  /api/v1/detection/player/{puuid}/latest  # Latest result
GET  /api/v1/detection/player/{puuid}/history  # Detection history
GET  /api/v1/detection/stats             # Overall statistics
```

### Jobs API (`app/api/jobs.py`)
```
GET    /api/v1/jobs/                     # List job configurations
GET    /api/v1/jobs/{job_id}             # Get specific config
POST   /api/v1/jobs/                     # Create job config
PUT    /api/v1/jobs/{job_id}             # Update job config
DELETE /api/v1/jobs/{job_id}             # Delete job config
GET    /api/v1/jobs/{job_id}/executions  # Execution history
GET    /api/v1/jobs/executions/all       # All executions
GET    /api/v1/jobs/executions/{execution_id}  # Execution details
POST   /api/v1/jobs/{job_id}/trigger     # Manual trigger
GET    /api/v1/jobs/status/overview      # System status
```

---

## 🎯 Quick Recipe: Add an Endpoint

### 1. Choose/Create Router File

**Location**: `backend/app/api/<domain>.py`

**Example domains**: `players.py`, `matches.py`, `detection.py`

### 2. Define the Endpoint

```python
# app/api/players.py
from fastapi import APIRouter, HTTPException, Query
from ..api.dependencies import PlayerServiceDep
from ..schemas.players import PlayerResponse

router = APIRouter(prefix="/players", tags=["players"])

@router.get("/{puuid}/stats", response_model=PlayerStatsResponse)
async def get_player_stats(
    puuid: str,
    player_service: PlayerServiceDep,
    days: int = Query(30, ge=1, le=365, description="Days to analyze")
):
    """
    Get player statistics over the specified time period.

    Args:
        puuid: Player's unique identifier
        player_service: Injected service (auto-provided)
        days: Number of days to analyze (1-365)

    Returns:
        PlayerStatsResponse with aggregated stats

    Raises:
        HTTPException: 404 if player not found
    """
    stats = await player_service.get_stats(puuid, days=days)
    if not stats:
        raise HTTPException(status_code=404, detail="Player not found")
    return stats
```

### 3. Register Router (if new file)

```python
# app/main.py
from app.api import players, matches, detection, jobs

app.include_router(players.router, prefix="/api/v1")
app.include_router(matches.router, prefix="/api/v1")
app.include_router(detection.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
```

### 4. Test the Endpoint

```bash
# Start dev server (auto-reloads on save)
./scripts/dev.sh

# Access docs
open http://localhost:8000/docs

# Manual test
curl http://localhost:8000/api/v1/players/{puuid}/stats?days=7
```

---

## 🧩 FastAPI Patterns

### Dependency Injection

**Use services, not direct DB access in endpoints**

```python
# ✅ GOOD - Use dependency injection
from ..api.dependencies import PlayerServiceDep

@router.get("/{puuid}")
async def get_player(
    puuid: str,
    player_service: PlayerServiceDep,  # Auto-injected
):
    return await player_service.get_player(puuid)

# ❌ BAD - Don't access DB directly in endpoints
from ..database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

@router.get("/{puuid}")
async def get_player(
    puuid: str,
    db: AsyncSession = Depends(get_db),
):
    # Don't put business logic here!
    result = await db.execute(...)
```

### Available Dependency Types

```python
# File: app/api/dependencies.py
from typing import Annotated
from fastapi import Depends

# Service dependencies (most common)
PlayerServiceDep = Annotated[PlayerService, Depends(get_player_service)]
MatchServiceDep = Annotated[MatchService, Depends(get_match_service)]
DetectionServiceDep = Annotated[SmurfDetectionService, Depends(get_detection_service)]
JobServiceDep = Annotated[JobService, Depends(get_job_service)]

# Database dependency (use in services, not endpoints)
DatabaseDep = Annotated[AsyncSession, Depends(get_db)]
```

### Query Parameters

```python
from fastapi import Query

@router.get("/players/")
async def list_players(
    skip: int = Query(0, ge=0, description="Number to skip"),
    limit: int = Query(10, ge=1, le=100, description="Max results"),
    tracked_only: bool = Query(False, description="Show tracked only"),
    player_service: PlayerServiceDep,
):
    return await player_service.list_players(
        skip=skip,
        limit=limit,
        tracked_only=tracked_only
    )
```

### Path Parameters

```python
from uuid import UUID

@router.get("/{puuid}")
async def get_player(
    puuid: str,  # String PUUID
    player_service: PlayerServiceDep,
):
    return await player_service.get_player(puuid)

@router.get("/{match_id}")
async def get_match(
    match_id: str,  # Match ID format: REGION_123456789
    match_service: MatchServiceDep,
):
    return await match_service.get_match(match_id)
```

### Request Body

```python
from ..schemas.players import PlayerUpdate

@router.post("/")
async def create_player(
    player_data: PlayerUpdate,  # Auto-validated by Pydantic
    player_service: PlayerServiceDep,
):
    return await player_service.create_player(player_data)
```

### Response Models

```python
from ..schemas.players import PlayerResponse, PlayerListResponse

# Single object response
@router.get("/{puuid}", response_model=PlayerResponse)
async def get_player(
    puuid: str,
    player_service: PlayerServiceDep,
):
    return await player_service.get_player(puuid)

# List response
@router.get("/", response_model=PlayerListResponse)
async def list_players(
    player_service: PlayerServiceDep,
):
    return await player_service.list_players()
```

---

## ⚠️ Error Handling

### Standard HTTP Exceptions

```python
from fastapi import HTTPException

# 404 Not Found
raise HTTPException(status_code=404, detail="Player not found")

# 400 Bad Request
raise HTTPException(status_code=400, detail="Invalid Riot ID format")

# 429 Too Many Requests (rate limit)
raise HTTPException(status_code=429, detail="Rate limit exceeded")

# 503 Service Unavailable
raise HTTPException(status_code=503, detail="Riot API unavailable")

# 422 Unprocessable Entity (validation error - auto by Pydantic)
# No need to raise manually, FastAPI handles this
```

### Service Layer Error Handling

**Let services raise exceptions, catch in endpoints if needed**

```python
from ..riot_api.errors import NotFoundError, RateLimitError

@router.get("/{puuid}")
async def get_player(
    puuid: str,
    player_service: PlayerServiceDep,
):
    try:
        return await player_service.get_player(puuid)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Player not found")
    except RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

### Custom Error Responses

```python
from fastapi.responses import JSONResponse

@router.get("/{puuid}")
async def get_player(puuid: str, player_service: PlayerServiceDep):
    player = await player_service.get_player(puuid)
    if not player:
        return JSONResponse(
            status_code=404,
            content={
                "error": "not_found",
                "message": "Player not found",
                "puuid": puuid
            }
        )
    return player
```

---

## 🔧 Testing Endpoints

### Using FastAPI TestClient

```python
# tests/api/test_players.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_get_player(client: AsyncClient):
    """Test player retrieval endpoint."""
    response = await client.get("/api/v1/players/test-puuid")
    assert response.status_code == 200
    data = response.json()
    assert data["puuid"] == "test-puuid"
    assert "game_name" in data

@pytest.mark.asyncio
async def test_search_player_by_riot_id(client: AsyncClient):
    """Test player search by Riot ID."""
    response = await client.get(
        "/api/v1/players/search",
        params={"riot_id": "TestPlayer#EUW", "platform": "eun1"}
    )
    assert response.status_code == 200
```

### Manual Testing

```bash
# Using httpie (recommended)
http GET localhost:8000/api/v1/players/search riot_id==Player#EUW platform==eun1

# Using curl
curl -X GET "http://localhost:8000/api/v1/players/search?riot_id=Player%23EUW&platform=eun1"

# Using FastAPI docs (interactive)
open http://localhost:8000/docs
```

---

## 📊 Common Patterns

### Pagination

```python
@router.get("/")
async def list_players(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    player_service: PlayerServiceDep,
):
    players = await player_service.list_players(skip=skip, limit=limit)
    total = await player_service.count_players()
    return {
        "items": players,
        "total": total,
        "skip": skip,
        "limit": limit
    }
```

### Optional Filters

```python
@router.get("/matches/")
async def search_matches(
    puuid: str | None = Query(None),
    queue_id: int | None = Query(None),
    min_duration: int | None = Query(None),
    match_service: MatchServiceDep,
):
    return await match_service.search_matches(
        puuid=puuid,
        queue_id=queue_id,
        min_duration=min_duration
    )
```

### Background Tasks

```python
from fastapi import BackgroundTasks

def send_notification(email: str, message: str):
    # Send email (non-async, blocking operation)
    pass

@router.post("/{puuid}/track")
async def track_player(
    puuid: str,
    background_tasks: BackgroundTasks,
    player_service: PlayerServiceDep,
):
    await player_service.track_player(puuid)
    background_tasks.add_task(send_notification, "admin@example.com", f"Tracking {puuid}")
    return {"status": "tracking"}
```

---

## 🚨 Common Pitfalls

1. **Don't put business logic in endpoints**
   - ✅ Endpoints should be thin wrappers
   - ❌ Don't write complex logic in the route handler

2. **Don't access database directly**
   - ✅ Use service layer with dependency injection
   - ❌ Don't use `Depends(get_db)` in endpoints

3. **Don't forget response models**
   - ✅ Always specify `response_model=SomeSchema`
   - ❌ Returning raw DB models exposes internal structure

4. **Don't swallow exceptions**
   - ✅ Let service exceptions bubble up or handle explicitly
   - ❌ Don't catch and return `None`

5. **Don't block the event loop**
   - ✅ Use `async def` and `await` for I/O
   - ❌ Don't use blocking operations (no `time.sleep()`, use `asyncio.sleep()`)

---

## 🔗 Related Files

- **`dependencies.py`** - Dependency injection factories
- **`../services/`** - Business logic layer (called by endpoints)
- **`../schemas/`** - Pydantic request/response models
- **`../main.py`** - App initialization, router registration
- **`../tests/api/`** - Endpoint tests

---

## 🔍 Keywords

API endpoints, FastAPI, REST, HTTP, routers, dependency injection, Depends, request validation, response models, error handling, Pydantic, query parameters, path parameters, testing
