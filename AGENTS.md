# Quick Start

```bash
./scripts/dev.sh              # Start with hot reload
./scripts/dev.sh --build      # Rebuild (uses Docker Bake for parallel builds)
./scripts/dev.sh --reset-db   # Wipe database
./scripts/dev.sh --down       # Stop services
```

**Production**: See `docker/AGENTS.md` for deployment workflow.

# Project Structure

- `backend/app/api/`: FastAPI endpoints
- `backend/app/services/`: Business logic
- `backend/app/riot_api/`: Riot API integration
- `backend/app/models/`: SQLAlchemy ORM models
- `backend/app/schemas/`: Pydantic validation schemas
- `backend/app/algorithms/`: Smurf detection algorithms
- `backend/app/jobs/`: Background jobs
- `frontend/app/`: Next.js pages
- `frontend/components/`: React components
- `frontend/lib/`: Utilities and API client

# Hot Reload

No restart needed - just save files:
- **Frontend**: Changes auto-refresh in browser
- **Backend**: Server restarts automatically
- **Rebuild only for**: Dependencies, Dockerfile changes, or system packages

# Code Style

- **Backend**: async/await, type hints, FastAPI patterns
- **Frontend**: TypeScript, function components with hooks
- **General**: Explicit imports, no .env edits

# Constraints

- ❌ Don't edit `docker/postgres/` manually
- ❌ Don't commit API keys or secrets
- ❌ Don't modify Riot API rate limiting
- ❌ Don't touch legacy code without explicit request

# Detailed Documentation

- `scripts/AGENTS.md`: All build and development commands
- `docker/AGENTS.md`: Docker, builds, and production deployment
- `backend/AGENTS.md`: Riot API integration and FastAPI patterns
- `frontend/AGENTS.md`: Next.js patterns and shadcn/ui
- `docker/postgres/AGENTS.md`: Database schema and tuning
