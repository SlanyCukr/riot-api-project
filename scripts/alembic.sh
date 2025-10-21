#!/bin/bash

# Alembic Helper Script
# Wrapper for running Alembic commands inside the backend container
# with proper Docker Compose configuration.
#
# Usage:
#   ./scripts/alembic.sh [ALEMBIC_COMMAND] [ARGS...]
#
# Examples:
#   ./scripts/alembic.sh current
#   ./scripts/alembic.sh history
#   ./scripts/alembic.sh upgrade head
#   ./scripts/alembic.sh downgrade -1
#   ./scripts/alembic.sh revision --autogenerate -m "description"

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.yml"
COMPOSE_OVERRIDE="$PROJECT_ROOT/docker/docker-compose.override.yml"

# Check if .env exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "❌ Error: .env file not found"
    echo "   Please copy .env.example to .env and configure it"
    exit 1
fi

# Run Alembic command in backend container
docker compose \
    --env-file "$PROJECT_ROOT/.env" \
    -f "$COMPOSE_FILE" \
    -f "$COMPOSE_OVERRIDE" \
    exec backend uv run alembic "$@"
