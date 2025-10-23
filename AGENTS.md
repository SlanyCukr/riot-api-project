<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# Quick Start

**Development** (automatic hot reload with watch mode):
```bash
docker compose watch                                # Start with hot reload
docker compose logs -f backend                      # View backend logs
docker compose exec backend uv run alembic current  # Check migration status
docker compose down                                 # Stop services
```

**Production**:
```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d
docker compose -f compose.yaml -f compose.prod.yaml logs -f
docker compose -f compose.yaml -f compose.prod.yaml down
```

**Building** (uses Docker Bake for parallel builds):
```bash
docker buildx bake -f docker/docker-bake.hcl dev --load   # Dev build
docker buildx bake -f docker/docker-bake.hcl prod --load  # Prod build
```

See `docker/AGENTS.md` for comprehensive command reference and deployment workflows.

# Project Structure

## Backend (Feature-Based Architecture)

- `backend/app/core/`: Infrastructure (database, config, Riot API client, shared enums)
- `backend/app/features/`: Domain features
  - `features/players/`: Player management (search, tracking, rank info)
  - `features/matches/`: Match data and statistics
  - `features/smurf_detection/`: Smurf analysis algorithms
  - `features/matchmaking_analysis/`: Matchmaking fairness evaluation
  - `features/jobs/`: Background job scheduling and execution
  - `features/settings/`: System configuration management
  - Each feature contains: `router.py`, `service.py`, `models.py`, `schemas.py`, `dependencies.py`

## Frontend (Feature-Based Architecture)

- `frontend/app/`: Next.js pages (App Router)
- `frontend/features/`: Feature modules
  - `features/players/`: Player components, hooks, utilities
  - `features/matches/`: Match components
  - `features/smurf-detection/`: Analysis components
  - `features/matchmaking/`: Matchmaking analysis components
  - `features/jobs/`: Job management components
  - `features/settings/`: Settings components
- `frontend/components/`: Shared layout components and shadcn/ui
- `frontend/lib/core/`: Core utilities (API client, schemas, validations)

# Hot Reload

No restart needed - just save files:

- **Frontend**: Changes auto-refresh in browser
- **Backend**: Server restarts automatically
- **Rebuild only for**: Dependencies, Dockerfile changes, or system packages

# Code Style

- **Backend**: async/await, type hints, FastAPI patterns
- **Frontend**: TypeScript, function components with hooks
- **General**: Explicit imports, no .env edits

## Feature Organization

- **Core vs. Features**: Infrastructure code in `core/`, domain code in `features/`
- **Dependency Flow**: Features depend on core, never the reverse
- **Public API**: Features expose public APIs through `__init__.py` exports
- **Import Examples**:
  ```python
  # Backend - import from features
  from app.features.players import PlayerService, Player, PlayerResponse
  from app.core.database import get_db
  from app.core.riot_api import RiotAPIClient

  # Frontend - import from features
  import { PlayerSearch } from '@/features/players'
  import { api } from '@/lib/core/api'
  ```

# Database Migrations

**ALWAYS use Alembic** for all database schema changes. Never use `create_all()`, `--reset-db`, or manual SQL.

```bash
# Create migration after changing models
docker compose exec backend uv run alembic revision --autogenerate -m "description"

# Apply migrations
docker compose exec backend uv run alembic upgrade head

# Check current migration status
docker compose exec backend uv run alembic current

# View migration history
docker compose exec backend uv run alembic history

# Rollback one migration
docker compose exec backend uv run alembic downgrade -1
```

**Important**: The entrypoint automatically runs `alembic upgrade head` on startup, so migrations are applied when containers start.

See `backend/alembic/AGENTS.md` for comprehensive migration documentation.

# Constraints

- ❌ **Never** use `create_all()`, `--reset-db`, or manual SQL — **ALWAYS use Alembic migrations**
- ❌ Don't commit API keys or secrets
- ❌ Don't modify Riot API rate limiting
- ❌ Don't touch legacy code without explicit request
- ❌ Don't skip pre-commit hooks (always run checks before committing)
- ❌ Don't manage tables owned by external libraries (e.g., APScheduler) — they handle their own schema

# Production Environment

**When working on production issues, deployments, or server operations**, read `docs/production-rpi.md` for complete production server documentation.

# Detailed Documentation

- `docs/production-rpi.md`: **Production server access, deployment, and troubleshooting**
- `docker/AGENTS.md`: **Comprehensive Docker Compose command reference**, builds, database operations, and production deployment
- `backend/AGENTS.md`: Riot API integration and FastAPI patterns
- `backend/alembic/AGENTS.md`: Database migrations with Alembic
- `frontend/AGENTS.md`: Next.js patterns and shadcn/ui
