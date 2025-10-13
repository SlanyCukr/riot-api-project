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

# AGENTS.md

Central quick reference for working with this Riot API application. See `README.md` for project overview and architecture.

## Project Overview

Full-stack Riot API application for League of Legends match analysis and smurf detection. Features include player search, match analysis, smurf detection algorithms, and encounter tracking with Riot API integration.

## Tech Stack
- **Backend**: Python 3.13 + FastAPI + SQLAlchemy
- **Frontend**: Next.js 15 + React 19 + TypeScript + shadcn/ui
- **Database**: PostgreSQL 18
- **Infrastructure**: Docker + Docker Compose

## Documentation Structure
This is the **central quick reference**. For detailed information:
- **`scripts/AGENTS.md`** - Development/production scripts, database operations, testing, debugging
- **`docker/AGENTS.md`** - Docker Compose commands, production deployment, troubleshooting
- **`backend/AGENTS.md`** - Riot API integration, smurf detection algorithms, FastAPI patterns
- **`frontend/AGENTS.md`** - Next.js patterns, shadcn/ui, TanStack Query, form handling
- **`docker/postgres/AGENTS.md`** - Database schema, performance tuning, advanced queries

## Quick Start

### Start Development Environment
```bash
./scripts/dev.sh              # Start with hot reload and watch mode
./scripts/dev.sh --help       # Show all options
```

### Start Production Environment
```bash
./scripts/prod.sh             # Start production environment
./scripts/prod.sh --help      # Show all options
```

## Hot Reload (IMPORTANT)

⚠️ **Both backend and frontend support hot reload** - containers do NOT need to be restarted or rebuilt for code changes.

- **Frontend**: Next.js hot reload - saving any file automatically updates in browser
- **Backend**: FastAPI auto-reload - saving Python files automatically restarts the server

**Simply save your file and the changes will apply immediately.** Only rebuild containers when:
- Changing dependencies (package.json, pyproject.toml, uv.lock)
- Modifying Dockerfile or docker-compose.yml
- Adding new system packages
