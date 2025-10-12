# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Full-stack Riot API application for League of Legends match analysis and smurf detection. Features include player search, match analysis, smurf detection algorithms, and encounter tracking with Riot API integration.

## Project Scope

Overview of what exactly is in project's scope is in `docs/project-scope.md`, as well as tasks labeled as "SPY-XXX" or "BACKLOG", reserved for tasks with the lowest priority, or "EPIC", reserved for labeling a group of tasks. When doing tasks described in `docs/project-scope.md`, mark them as "WIP", instead of "TODO", and after user tests your code and approves it, mark it as done with ✅.

## Technology Stack

- **Backend**: Python 3.13 + FastAPI + SQLAlchemy
- **Frontend**: React 19 + TypeScript + Tailwind CSS + Vite
- **Database**: PostgreSQL 18
- **Infrastructure**: Docker + Docker Compose

## Project Structure

- `backend/` - Python FastAPI backend with API services
- `frontend/` - React TypeScript frontend application
- `docker/` - Docker configuration and deployment guides
- `scripts/` - Utility scripts for development and deployment

## Specialized Documentation

**Always refer to these specialized docs for detailed implementation guidance:**

- **Backend**: `backend/CLAUDE.md` - API structure, services, Riot API client, smurf detection algorithms
- **Frontend**: `frontend/CLAUDE.md` - Component architecture, API integration, styling patterns
- **Database**: `docker/postgres/CLAUDE.md` - Schema design, migrations, performance optimization
- **Docker**: `docker/CLAUDE.md` - Container management, commands, production deployment

## Quick Start

```bash
# First time or if you encounter port conflicts:
./scripts/docker-cleanup.sh     # Clean up Docker resources and stop local PostgreSQL

docker compose up --build       # Start all services
docker compose up backend       # Start specific service
docker compose down             # Stop all services
```

**Hot Reload**: Both backend and frontend support hot reload. Changes to source files are automatically detected and applied without restarting containers.

**Port Conflicts?** See `docs/docker-troubleshooting.md` or run `./scripts/docker-cleanup.sh`

See `docker/CLAUDE.md` for complete Docker workflow and troubleshooting.

## Environment Configuration

Copy `.env.example` to `.env` and configure:
- `RIOT_API_KEY` - Get from https://developer.riotgames.com (expires every 24h for dev keys)
- Database credentials and connection settings
- Service ports and URLs

See specialized docs for service-specific environment variables.

## Code Quality

Pre-commit hooks ensure code quality.

Run manually: `uvx pre-commit run --all-files`

Hooks run automatically on git commit. Update hooks: `uvx pre-commit autoupdate`
