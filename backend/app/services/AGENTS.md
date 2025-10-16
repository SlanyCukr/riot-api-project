# Tech Stack
- SQLAlchemy 2.0+ with async support
- Dependency injection pattern
- RiotDataManager for API calls
- structlog for context logging

# Project Structure
- `players.py` - Player CRUD and tracking logic
- `matches.py` - Match retrieval and statistics
- `detection.py` - Smurf detection orchestration
- `jobs.py` - Job configuration management
- `settings.py` - Runtime settings operations

# Commands
- `uv run pytest tests/services/` - Run service tests
- Use AsyncMock for mocking dependencies

# Code Style
- Use async/await for all I/O
- Commit transactions explicitly
- Log with structured context
- Return domain models, not DB models

# Do Not
- Don't call RiotAPIClient directly (use RiotDataManager)
- Don't mix transaction contexts
- Don't catch generic exceptions
- Don't return DB models to API layer
