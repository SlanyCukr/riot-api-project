# Riot API Backend

Backend service for Riot API match history and smurf detection.

## Features

- FastAPI-based REST API
- PostgreSQL database with async support
- Redis caching
- Riot API integration
- Smurf detection algorithms
- Match history tracking

## Development

### Requirements

- Python 3.11+
- uv package manager

### Setup

```bash
uv sync
```

### Running

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or run the main file:

```bash
uv run python main.py
```

## Environment Variables

Copy `.env.example` to `.env` and configure your environment variables.
