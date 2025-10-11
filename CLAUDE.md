# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Full-stack Riot API application for League of Legends match analysis and smurf detection. Python FastAPI backend + React TypeScript frontend + PostgreSQL, containerized with Docker.

## Project Structure

- `backend/` - Python FastAPI backend with API services
- `frontend/` - React TypeScript frontend application
- `docker/` - Docker configuration and deployment guides
- `scripts/` - Utility scripts for development and deployment

## Specialized Documentation

- **Backend**: `backend/CLAUDE.md` - FastAPI, services, Riot API integration
- **Frontend**: `frontend/CLAUDE.md` - React, TypeScript, styling
- **Database**: `docker/postgres/CLAUDE.md` - PostgreSQL schema, migrations, optimization
- **Docker**: `docker/CLAUDE.md` - Container management, production deployment

## Quick Start

```bash
docker compose up --build  # Start all services
```

See `docker/CLAUDE.md` for detailed Docker commands and development workflow.

## Technology Stack

Python FastAPI + React TypeScript + PostgreSQL, containerized with Docker

## Features

Player search, match analysis, smurf detection, and encounter tracking with Riot API integration

## Environment

See `.env.example` for required variables (RIOT_API_KEY, database config)

## Development

Docker-based development with hot reload. See specialized docs for implementation details.

## Code Quality

Pre-commit hooks (ruff, ruff-format, pyright) ensure code quality. Run `uvx pre-commit run --all-files` to check.
