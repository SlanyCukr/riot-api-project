# Tech Stack

- FastAPI with async/await support
- Pydantic for request/response validation
- Dependency injection with Depends()
- Auto-generated OpenAPI docs

# Project Structure

- `players.py` - Player search, tracking, rank endpoints
- `matches.py` - Match history, stats, encounters
- `detection.py` - Player analysis endpoints
- `jobs.py` - Job management and execution endpoints
- `settings.py` - Runtime settings management
- `dependencies.py` - FastAPI dependency factories

# Commands

- GET `/docs` - Interactive API documentation
- `./scripts/dev.sh` - Start dev server with hot reload

# Code Style

- Use dependency injection for services
- Always specify response_model parameter
- Handle errors with HTTPException
- Keep endpoints thin (delegate to services)

# Do Not

- Don't put business logic in endpoints
- Don't access database directly (use services)
- Don't return raw DB models (use schemas)
- Don't swallow exceptions
