# Testing Guide

**WHEN TO USE THIS**: Writing tests, debugging test failures, or setting up test fixtures.

**QUICK START**: Adding test? → [Jump to Quick Recipes](#-quick-recipes)

---

## 📁 Test Structure

```
backend/app/tests/
├── conftest.py              # Shared fixtures (db, client, mocks)
│
├── api/                     # API endpoint tests
│   ├── test_players.py     # Player endpoints
│   ├── test_matches.py     # Match endpoints
│   └── test_detection.py   # Detection endpoints
│
├── services/                # Service layer tests
│   ├── test_players.py     # PlayerService
│   ├── test_detection.py   # SmurfDetectionService
│   └── test_algorithm_integration.py  # Algorithm integration
│
├── riot_api/                # Riot API client tests
│   ├── test_client.py      # RiotAPIClient
│   ├── test_rate_limiter.py  # Rate limiting
│   └── test_models.py      # Pydantic models
│
└── jobs/                    # Background job tests
    ├── test_base.py        # BaseJob functionality
    ├── test_scheduler.py   # Job scheduler
    └── test_tracked_player_updater.py  # Job tests
```

---

## 🚀 Running Tests

### Inside Docker (Recommended)

```bash
# Run all tests
docker compose exec backend uv run pytest

# Run with verbose output
docker compose exec backend uv run pytest -v

# Run specific test file
docker compose exec backend uv run pytest tests/api/test_players.py

# Run specific test function
docker compose exec backend uv run pytest tests/api/test_players.py::test_search_player

# Run tests matching pattern
docker compose exec backend uv run pytest -k "player"

# Run with coverage
docker compose exec backend uv run pytest --cov=app --cov-report=html

# Stop on first failure
docker compose exec backend uv run pytest -x

# Show local variables on failure
docker compose exec backend uv run pytest -l
```

### Local Development (Requires uv)

```bash
cd backend
uv run pytest
uv run pytest -v --cov=app
```

---

## 🎯 Quick Recipes

### API Endpoint Test

```python
# tests/api/test_players.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_player(client: AsyncClient, sample_player):
    """Test getting a player by PUUID."""
    # Make request
    response = await client.get(f"/api/v1/players/{sample_player.puuid}")

    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["puuid"] == sample_player.puuid
    assert data["game_name"] == sample_player.game_name

@pytest.mark.asyncio
async def test_search_player_not_found(client: AsyncClient):
    """Test searching for non-existent player."""
    response = await client.get(
        "/api/v1/players/search",
        params={"riot_id": "NonExistent#NA1"}
    )

    assert response.status_code == 404
```

### Service Layer Test

```python
# tests/services/test_players.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.players import PlayerService
from app.models.players import Player

@pytest.mark.asyncio
async def test_get_player(db: AsyncSession, riot_data_manager_mock):
    """Test player service retrieval."""
    # Setup
    service = PlayerService(db, riot_data_manager_mock)

    # Create test data
    player = Player(
        puuid="test-puuid",
        game_name="TestPlayer",
        tag_line="EUW"
    )
    db.add(player)
    await db.commit()

    # Execute
    result = await service.get_player("test-puuid")

    # Assert
    assert result is not None
    assert result.puuid == "test-puuid"
    assert result.game_name == "TestPlayer"
```

### Mock Riot API

```python
# tests/services/test_players.py
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_fetch_player_from_api(db: AsyncSession):
    """Test fetching player from Riot API."""
    # Create mock
    mock_data_manager = AsyncMock()
    mock_data_manager.get_player_by_riot_id.return_value = Player(
        puuid="api-puuid",
        game_name="APIPlayer",
        tag_line="NA"
    )

    # Test
    service = PlayerService(db, mock_data_manager)
    player = await service.get_player_by_riot_id("APIPlayer", "NA", "na1")

    # Verify
    assert player.puuid == "api-puuid"
    mock_data_manager.get_player_by_riot_id.assert_called_once_with(
        game_name="APIPlayer",
        tag_line="NA",
        platform="na1"
    )
```

### Test with Database Transaction

```python
@pytest.mark.asyncio
async def test_update_player(db: AsyncSession, sample_player):
    """Test updating player data."""
    # Modify
    sample_player.game_name = "UpdatedName"
    await db.commit()
    await db.refresh(sample_player)

    # Verify
    assert sample_player.game_name == "UpdatedName"

    # Fetch again to confirm persistence
    from sqlalchemy import select
    stmt = select(Player).where(Player.puuid == sample_player.puuid)
    result = await db.execute(stmt)
    player = result.scalar_one()
    assert player.game_name == "UpdatedName"
```

---

## 🧩 Common Fixtures

**Located in `conftest.py`**

### Database Fixtures

```python
@pytest.fixture
async def db() -> AsyncSession:
    """
    Async database session for tests.
    Uses in-memory SQLite for isolation.
    Automatically rolls back after each test.
    """
    # Usage: async def test_something(db: AsyncSession)
```

### HTTP Client Fixtures

```python
@pytest.fixture
async def client() -> AsyncClient:
    """
    Async HTTP client for testing API endpoints.
    Automatically handles app lifecycle.
    """
    # Usage: async def test_endpoint(client: AsyncClient)
```

### Mock Fixtures

```python
@pytest.fixture
def riot_data_manager_mock() -> AsyncMock:
    """
    Mocked RiotDataManager for tests.
    Pre-configured with common responses.
    """
    # Usage: def test_something(riot_data_manager_mock)

@pytest.fixture
def riot_client_mock() -> AsyncMock:
    """Mocked RiotAPIClient for tests."""
```

### Sample Data Fixtures

```python
@pytest.fixture
async def sample_player(db: AsyncSession) -> Player:
    """
    Creates a sample player in the database.
    Automatically cleaned up after test.
    """
    # Usage: async def test_something(sample_player: Player)

@pytest.fixture
async def sample_match(db: AsyncSession, sample_player: Player) -> Match:
    """Creates a sample match with participants."""

@pytest.fixture
async def sample_detection(db: AsyncSession, sample_player: Player) -> SmurfDetection:
    """Creates a sample detection result."""
```

---

## 🎨 Testing Patterns

### Testing Async Functions

```python
import pytest

# Always mark async tests with @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == expected_value
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("Player#NA1", ("Player", "NA1")),
    ("Test#EUW", ("Test", "EUW")),
    ("Name#123", ("Name", "123")),
])
def test_parse_riot_id(input, expected):
    """Test parsing Riot ID with multiple inputs."""
    result = parse_riot_id(input)
    assert result == expected
```

### Testing Exceptions

```python
@pytest.mark.asyncio
async def test_player_not_found(db: AsyncSession, riot_data_manager_mock):
    """Test that service raises exception for missing player."""
    service = PlayerService(db, riot_data_manager_mock)

    with pytest.raises(ValueError, match="Player .* not found"):
        await service.get_player("nonexistent-puuid")
```

### Testing with Multiple Fixtures

```python
@pytest.mark.asyncio
async def test_complex_scenario(
    db: AsyncSession,
    client: AsyncClient,
    sample_player: Player,
    riot_data_manager_mock: AsyncMock
):
    """Test using multiple fixtures."""
    # Setup
    riot_data_manager_mock.get_match_history.return_value = []

    # Execute
    response = await client.get(f"/api/v1/players/{sample_player.puuid}/recent")

    # Assert
    assert response.status_code == 200
    assert response.json() == []
```

---

## 🎭 Mocking Patterns

### Mock RiotDataManager

```python
from unittest.mock import AsyncMock

@pytest.fixture
def riot_data_manager_mock():
    """Complete mock setup for RiotDataManager."""
    mock = AsyncMock()

    # Mock player lookup
    mock.get_player_by_riot_id.return_value = Player(
        puuid="mock-puuid",
        game_name="MockPlayer",
        tag_line="NA"
    )

    # Mock match history
    mock.get_match_history.return_value = [
        Match(match_id="MATCH_1", game_duration=1800),
        Match(match_id="MATCH_2", game_duration=2100),
    ]

    # Mock rate limit (returns None)
    async def rate_limited(*args, **kwargs):
        return None
    mock.get_player_by_puuid.side_effect = rate_limited

    return mock
```

### Mock with Side Effects

```python
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_with_side_effect():
    """Test with mock that changes behavior on multiple calls."""
    mock = AsyncMock()

    # First call returns player, second returns None (rate limited)
    mock.get_player_by_riot_id.side_effect = [
        Player(puuid="p1", game_name="Player1"),
        None  # Rate limited
    ]

    # First call succeeds
    result1 = await mock.get_player_by_riot_id("Player1", "NA", "na1")
    assert result1 is not None

    # Second call rate limited
    result2 = await mock.get_player_by_riot_id("Player2", "NA", "na1")
    assert result2 is None
```

### Patch External Dependencies

```python
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
@patch('app.riot_api.client.RiotAPIClient')
async def test_with_patched_client(mock_client_class):
    """Test with patched RiotAPIClient class."""
    # Setup mock
    mock_instance = AsyncMock()
    mock_instance.get_account.return_value = {"puuid": "test", "gameName": "Test"}
    mock_client_class.return_value = mock_instance

    # Test code that creates RiotAPIClient
    from app.riot_api.client import RiotAPIClient
    client = RiotAPIClient()
    result = await client.get_account("Test", "NA")

    assert result["puuid"] == "test"
```

---

## 📊 Coverage

### Generate Coverage Report

```bash
# Generate coverage report
docker compose exec backend uv run pytest --cov=app --cov-report=html

# View report (from host)
open backend/htmlcov/index.html  # macOS
xdg-open backend/htmlcov/index.html  # Linux
```

### Coverage Goals

| Component | Target Coverage |
|-----------|----------------|
| API endpoints | 90%+ |
| Services | 85%+ |
| Algorithms | 80%+ |
| Overall | 80%+ |

### Check Coverage in CI

```bash
# Fail if coverage below threshold
docker compose exec backend uv run pytest --cov=app --cov-fail-under=80
```

---

## 🐛 Debugging Tests

### Print Debug Info

```python
@pytest.mark.asyncio
async def test_with_debug(db: AsyncSession, sample_player: Player):
    """Test with debug output."""
    print(f"Player PUUID: {sample_player.puuid}")

    result = await service.get_player(sample_player.puuid)

    print(f"Result: {result}")
    print(f"Game name: {result.game_name}")

    assert result.puuid == sample_player.puuid
```

**Run with `-s` flag to see prints**:
```bash
docker compose exec backend uv run pytest -s tests/api/test_players.py::test_with_debug
```

### Inspect Failures

```bash
# Show local variables on failure
docker compose exec backend uv run pytest -l

# Stop on first failure
docker compose exec backend uv run pytest -x

# Drop into debugger on failure
docker compose exec backend uv run pytest --pdb
```

### Check Database State

```python
@pytest.mark.asyncio
async def test_with_db_inspection(db: AsyncSession):
    """Test with database inspection."""
    from sqlalchemy import select, func

    # Check player count
    count = await db.scalar(select(func.count(Player.puuid)))
    print(f"Player count: {count}")

    # Check all players
    stmt = select(Player)
    result = await db.execute(stmt)
    players = list(result.scalars().all())
    print(f"Players: {[p.game_name for p in players]}")
```

---

## 🚨 Common Pitfalls

1. **Don't forget `@pytest.mark.asyncio` on async tests**
   - ✅ Always mark: `@pytest.mark.asyncio`
   - ❌ Forgetting causes cryptic errors

2. **Don't modify shared fixtures**
   - ✅ Each test gets its own fixture instance
   - ❌ Don't rely on modifications persisting

3. **Don't forget to await async calls**
   - ✅ `result = await service.method()`
   - ❌ `result = service.method()` returns coroutine

4. **Don't commit in fixtures without cleanup**
   - ✅ Transactions auto-rollback in test fixtures
   - ❌ Manual commits may leak state

5. **Don't test implementation details**
   - ✅ Test behavior and outcomes
   - ❌ Don't test private methods or internal state

6. **Don't use real API keys in tests**
   - ✅ Mock external API calls
   - ❌ Tests should never hit real Riot API

---

## 📝 Test Organization

### Test File Naming

```
test_<module_name>.py

Examples:
- test_players.py
- test_matches.py
- test_detection.py
```

### Test Function Naming

```python
def test_<what>_<condition>_<expected>():
    """Clear description of what's being tested."""
    pass

Examples:
- test_get_player_success()
- test_get_player_not_found()
- test_search_player_by_riot_id()
- test_update_player_invalid_data()
```

### Test Structure (AAA Pattern)

```python
@pytest.mark.asyncio
async def test_something(db: AsyncSession):
    """Test description."""
    # Arrange - Setup test data
    player = Player(puuid="test", game_name="Test")
    db.add(player)
    await db.commit()

    # Act - Execute the code being tested
    result = await service.get_player("test")

    # Assert - Verify the results
    assert result.puuid == "test"
    assert result.game_name == "Test"
```

---

## 🔗 Related Files

- **`conftest.py`** - Shared fixtures and test configuration
- **`../services/`** - Services being tested
- **`../api/`** - API endpoints being tested
- **`../models/`** - Database models used in tests

---

## 🔍 Keywords

Testing, pytest, async tests, fixtures, mocking, AsyncMock, test coverage, API testing, service testing, database testing, integration tests, unit tests, test-driven development
