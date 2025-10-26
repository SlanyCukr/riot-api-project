# Migration Guide: Feature-Based Architecture

This guide helps developers navigate the transition from layer-based to feature-based architecture.

## Table of Contents

- [Overview](#overview)
- [What Changed](#what-changed)
- [Import Path Changes](#import-path-changes)
- [Finding Code](#finding-code)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

## Overview

The codebase has been reorganized from **layer-based** (organizing by technical layer) to **feature-based** (organizing by domain/capability).

### Before (Layer-Based)

```
backend/app/
├── api/          # All API endpoints
├── services/     # All business logic
├── models/       # All database models
└── schemas/      # All Pydantic schemas

frontend/
├── app/          # Pages
├── components/   # ALL components (mixed)
└── lib/          # ALL utilities
```

### After (Feature-Based)

```
backend/app/
├── core/         # Infrastructure (database, config, Riot API)
└── features/     # Domain features
    ├── players/
    ├── matches/
    ├── player_analysis/
    ├── matchmaking_analysis/
    ├── jobs/
    └── settings/

frontend/
├── app/          # Pages (unchanged)
├── features/     # Feature modules
│   ├── players/
│   ├── matches/
│   └── ...
├── components/   # Shared components only
└── lib/core/     # Core utilities
```

## What Changed

### Backend Changes

#### Core Infrastructure

All infrastructure code moved to `app/core/`:

- ✅ `database.py` - Database session management
- ✅ `config.py` - Application settings
- ✅ `logging.py` - Structured logging
- ✅ `riot_api/` - Riot API client (was `app/riot_api/`)
- ✅ `enums.py` - Shared enums (extracted from models/schemas)

#### Feature Modules

Domain code organized into `app/features/`:

- ✅ Each feature has: `router.py`, `service.py`, `models.py`, `schemas.py`, `dependencies.py`
- ✅ Jobs centralized in `features/jobs/` with `implementations/` subdirectory
- ✅ Each feature has a `README.md` for documentation

#### Removed Directories

- ❌ `app/api/` - Deleted (routers moved to features)
- ❌ `app/services/` - Deleted (services moved to features)
- ❌ `app/models/` - Deleted (models moved to features or core)
- ❌ `app/schemas/` - Deleted (schemas moved to features)
- ❌ `app/jobs/` - Deleted (jobs moved to `features/jobs/`)

### Frontend Changes

#### Feature Modules

Components organized by domain in `features/`:

- ✅ Each feature has: `components/`, `hooks/` (optional), `utils/` (optional), `index.ts`
- ✅ Feature-specific UI separated from shared UI

#### Core Utilities

Shared utilities moved to `lib/core/`:

- ✅ `api.ts` - Axios client
- ✅ `schemas.ts` - Zod schemas
- ✅ `validations.ts` - Validation utilities

#### Shared Components

Only layout/infrastructure components remain in `components/`:

- ✅ `sidebar-nav.tsx`, `theme-toggle.tsx`, `providers.tsx`, etc.
- ✅ `ui/` - shadcn/ui (untouched)

#### Removed

- ❌ Feature-specific components removed from `components/` root

## Import Path Changes

### Backend Import Mapping

| Old Path                                         | New Path                                          | Notes                     |
| ------------------------------------------------ | ------------------------------------------------- | ------------------------- |
| `from app.api.players import router`             | `from app.features.players import players_router` | Use feature's public API  |
| `from app.services.players import PlayerService` | `from app.features.players import PlayerService`  | Import from feature       |
| `from app.models.players import Player`          | `from app.features.players import Player`         | Models in feature         |
| `from app.schemas.players import PlayerResponse` | `from app.features.players import PlayerResponse` | Schemas in feature        |
| `from app.models.ranks import Tier`              | `from app.core.enums import Tier`                 | Enums centralized in core |
| `from app.database import get_db`                | `from app.core.database import get_db`            | Core infrastructure       |
| `from app.riot_api import RiotAPIClient`         | `from app.core.riot_api import RiotAPIClient`     | Core infrastructure       |

### Frontend Import Mapping

| Old Path                                                    | New Path                                                | Notes              |
| ----------------------------------------------------------- | ------------------------------------------------------- | ------------------ |
| `import { PlayerSearch } from '@/components/player-search'` | `import { PlayerSearch } from '@/features/players'`     | Feature component  |
| `import { MatchHistory } from '@/components/match-history'` | `import { MatchHistory } from '@/features/matches'`     | Feature component  |
| `import { api } from '@/lib/api'`                           | `import { api } from '@/lib/core/api'`                  | Core utility       |
| `import { Button } from '@/components/ui/button'`           | `import { Button } from '@/components/ui/button'`       | Unchanged (shadcn) |
| `import { SidebarNav } from '@/components/sidebar-nav'`     | `import { SidebarNav } from '@/components/sidebar-nav'` | Unchanged (shared) |

## Finding Code

### "Where is the code for X?"

#### Backend

**Player-related code:**

- API endpoints: `backend/app/features/players/router.py`
- Business logic: `backend/app/features/players/service.py`
- Database models: `backend/app/features/players/models.py`
- Request/response schemas: `backend/app/features/players/schemas.py`
- Dependencies: `backend/app/features/players/dependencies.py`

**Match-related code:**

- Everything in: `backend/app/features/matches/`

**Player analysis:**

- Everything in: `backend/app/features/player_analysis/`
- Analyzers: `backend/app/features/player_analysis/analyzers/`

**Background jobs:**

- Job infrastructure: `backend/app/features/jobs/`
- Job implementations: `backend/app/features/jobs/implementations/`

**Riot API client:**

- Infrastructure: `backend/app/core/riot_api/`
- Not a feature (it's infrastructure used by all features)

#### Frontend

**Player components:**

- All player UI: `frontend/features/players/components/`
- Exported from: `frontend/features/players/index.ts`

**Match components:**

- All match UI: `frontend/features/matches/components/`

**Shared components:**

- Layout/infrastructure: `frontend/components/`
- shadcn/ui primitives: `frontend/components/ui/`

**API client:**

- Core infrastructure: `frontend/lib/core/api.ts`

### Search Commands

**Find where a class/function is defined:**

```bash
# Backend - find PlayerService definition
rg "class PlayerService" backend/app/
# Result: backend/app/features/players/service.py

# Frontend - find PlayerSearch component
rg "export.*PlayerSearch" frontend/
# Result: frontend/features/players/components/player-search.tsx
```

**Find all imports of a module:**

```bash
# Find all imports of PlayerService
rg "from.*players.*import.*PlayerService" backend/app/

# Find all imports of PlayerSearch
rg "import.*PlayerSearch" frontend/
```

## Common Tasks

### Task 1: Add a New API Endpoint

**Before (Layer-Based):**

1. Add route to `backend/app/api/players.py`
2. Add logic to `backend/app/services/players.py`
3. Add schema to `backend/app/schemas/players.py`

**After (Feature-Based):**

1. Add route to `backend/app/features/players/router.py`
2. Add logic to `backend/app/features/players/service.py`
3. Add schema to `backend/app/features/players/schemas.py`
4. Update `backend/app/features/players/__init__.py` if exposing new classes
5. Document in `backend/app/features/players/README.md`

**Example:**

```python
# features/players/router.py
@router.get("/players/{puuid}/stats")
async def get_player_stats(
    puuid: str,
    player_service: PlayerService = Depends(get_player_service)
):
    return await player_service.get_stats(puuid)

# features/players/service.py
async def get_stats(self, puuid: str) -> PlayerStats:
    # Implementation
    pass

# features/players/schemas.py
class PlayerStats(BaseModel):
    games_played: int
    win_rate: float
```

### Task 2: Add a New Frontend Component

**Before (Layer-Based):**

1. Create `frontend/components/my-component.tsx`
2. Import in page: `import { MyComponent } from '@/components/my-component'`

**After (Feature-Based):**

**If component is feature-specific:**

1. Create `frontend/features/players/components/my-component.tsx`
2. Export from `frontend/features/players/index.ts`:
   ```typescript
   export { MyComponent } from "./components/my-component";
   ```
3. Import in page: `import { MyComponent } from '@/features/players'`

**If component is shared:**

1. Create `frontend/components/my-component.tsx`
2. Import in page: `import { MyComponent } from '@/components/my-component'`

### Task 3: Create a New Feature

**Backend:**

1. Create directory: `backend/app/features/my_feature/`
2. Create files:
   ```
   my_feature/
   ├── __init__.py          # Public API exports
   ├── router.py            # FastAPI routes
   ├── service.py           # Business logic
   ├── models.py            # Database models
   ├── schemas.py           # Pydantic schemas
   ├── dependencies.py      # Dependency injection
   ├── tests/               # Tests directory
   │   └── __init__.py
   └── README.md            # Documentation
   ```
3. Register router in `backend/app/main.py`:
   ```python
   from app.features.my_feature import my_feature_router
   app.include_router(my_feature_router, prefix="/api/v1", tags=["my_feature"])
   ```

**Frontend:**

1. Create directory: `frontend/features/my-feature/`
2. Create structure:
   ```
   my-feature/
   ├── components/
   │   └── my-component.tsx
   ├── hooks/               # Optional
   ├── utils/               # Optional
   └── index.ts             # Public exports
   ```
3. Export from `index.ts`:
   ```typescript
   export { MyComponent } from "./components/my-component";
   ```

### Task 4: Import from Another Feature (Backend)

**❌ Don't import directly between features:**

```python
# DON'T DO THIS
from app.features.players.service import PlayerService  # Cross-feature import
```

**✅ Do use dependency injection:**

```python
# In features/matches/router.py
from app.features.players.dependencies import get_player_service

@router.get("/matches/{puuid}")
async def get_matches(
    puuid: str,
    player_service: PlayerService = Depends(get_player_service)
):
    player = await player_service.get_player(puuid)
    # Use player data...
```

**✅ Or use core as intermediary:**
If features need to share data, consider:

- Creating a core service that both features depend on
- Using database relationships (access via database, not service)

### Task 5: Debug Import Errors

**Error: `ModuleNotFoundError: No module named 'app.api'`**

**Cause:** Old import path referencing deleted `app/api/` directory.

**Fix:** Update to new feature path:

```python
# Old
from app.api.players import router

# New
from app.features.players import players_router
```

**Error: `ImportError: cannot import name 'PlayerService'`**

**Cause:** Importing from wrong path or not exported from feature's `__init__.py`.

**Fix:**

1. Check feature's `__init__.py` exports `PlayerService`
2. Use correct import path:
   ```python
   from app.features.players import PlayerService
   ```

## Troubleshooting

### Backend Issues

**Problem: "I can't find where the Player model is defined"**

**Solution:** Check feature's `models.py`:

```bash
rg "class Player" backend/app/features/
# Result: backend/app/features/players/models.py
```

**Problem: "Circular import error between features"**

**Solution:** Features should not import from each other. Use:

- Dependency injection (inject services via FastAPI Depends)
- Core services (move shared logic to `core/`)
- Database relationships (access related data via DB)

**Problem: "Can't import Tier enum"**

**Solution:** Tier moved to core:

```python
# Old
from app.models.ranks import Tier

# New
from app.core.enums import Tier
```

### Frontend Issues

**Problem: "Component import not found"**

**Solution:** Check if component moved to feature:

```bash
rg "export.*MyComponent" frontend/
```

Then import from correct feature:

```typescript
import { MyComponent } from "@/features/players";
```

**Problem: "API client import broken"**

**Solution:** API client moved to core:

```typescript
// Old
import { api } from "@/lib/api";

// New
import { api } from "@/lib/core/api";
```

### General Issues

**Problem: "Pre-commit hooks failing after migration"**

**Solution:**

1. Check import paths in modified files
2. Run type checking: `pyright backend/app/`
3. Run linting: `ruff check backend/app/`
4. Fix reported issues

**Problem: "Tests failing after migration"**

**Solution:**

1. Update test imports to new paths
2. Update mocks to use new paths
3. Verify fixtures still work with new structure

## Best Practices

### Import Guidelines

**Backend:**

```python
# ✅ Good: Import from feature's public API
from app.features.players import PlayerService, Player, PlayerResponse

# ✅ Good: Import from core
from app.core.database import get_db
from app.core.riot_api import RiotAPIClient

# ❌ Bad: Cross-feature imports
from app.features.players.service import PlayerService  # In matches feature

# ❌ Bad: Importing internals
from app.features.players.utils.internal_helper import helper_func
```

**Frontend:**

```typescript
// ✅ Good: Import from feature's public API
import { PlayerSearch, PlayerCard } from "@/features/players";

// ✅ Good: Import from core
import { api } from "@/lib/core/api";

// ❌ Bad: Import from another feature's component directly
import { PlayerCard } from "@/features/players/components/player-card"; // Use index.ts

// ✅ Good: Shared components
import { Button } from "@/components/ui/button";
```

### Code Organization

**When to create a new feature:**

- Represents a distinct domain/capability
- Has multiple related endpoints/components
- Will grow over time

**When to add to existing feature:**

- Directly related to existing feature
- Small addition to current capability
- Shares models/schemas with feature

**When to put in core:**

- Used by multiple features
- Infrastructure/utility code
- No business logic

## Migration Checklist

If you're updating old code or PRs:

- [ ] Update all import paths to new structure
- [ ] Move new code to appropriate feature directory
- [ ] Update tests to use new import paths
- [ ] Run type checking and linting
- [ ] Update documentation if needed
- [ ] Verify all endpoints still work
- [ ] Check feature's README.md for guidelines

## Quick Reference

### Backend Structure

```
app/
├── core/                    # Infrastructure
│   ├── database.py
│   ├── config.py
│   ├── riot_api/
│   └── enums.py
└── features/                # Domain features
    ├── players/
    │   ├── __init__.py
    │   ├── router.py
    │   ├── service.py
    │   ├── models.py
    │   ├── schemas.py
    │   ├── dependencies.py
    │   └── README.md
    └── ...
```

### Frontend Structure

```
frontend/
├── app/                     # Pages (unchanged)
├── features/                # Feature modules
│   ├── players/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── utils/
│   │   └── index.ts
│   └── ...
├── components/              # Shared only
│   ├── sidebar-nav.tsx
│   └── ui/                  # shadcn (unchanged)
└── lib/
    ├── core/                # Core utilities
    │   ├── api.ts
    │   └── schemas.ts
    └── utils.ts
```

## Additional Resources

- [Backend AGENTS.md](/backend/AGENTS.md) - Backend architecture details
- [Frontend AGENTS.md](/frontend/AGENTS.md) - Frontend architecture details
- [Root CLAUDE.md](/CLAUDE.md) - Project overview
- Feature READMEs:
  - [Players Feature](/backend/app/features/players/README.md)
  - [Matches Feature](/backend/app/features/matches/README.md)
  - [Player Analysis](/backend/app/features/player_analysis/README.md)
  - [Matchmaking Analysis](/backend/app/features/matchmaking_analysis/README.md)
  - [Jobs Feature](/backend/app/features/jobs/README.md)
  - [Settings Feature](/backend/app/features/settings/README.md)

## Questions?

If you encounter issues not covered in this guide:

1. Check the feature's README.md
2. Search for similar code: `rg "pattern" backend/app/features/`
3. Review recent commits for examples
4. Ask the team!
