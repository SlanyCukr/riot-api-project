#!/bin/bash

# Logs Helper Script
# Wrapper for viewing Docker Compose logs with proper configuration.
#
# Usage:
#   ./scripts/logs.sh [SERVICE] [DOCKER_LOGS_OPTIONS...]
#
# Examples:
#   ./scripts/logs.sh                    # All services, follow mode
#   ./scripts/logs.sh backend            # Backend only, follow mode
#   ./scripts/logs.sh backend --tail=50  # Last 50 lines
#   ./scripts/logs.sh --tail=100         # Last 100 lines from all services

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

# Default to follow mode if no flags provided
if [ $# -eq 0 ] || [[ ! "$*" =~ --(tail|since|until) ]]; then
    FOLLOW_FLAG="-f"
else
    FOLLOW_FLAG=""
fi

# View logs
docker compose \
    --env-file "$PROJECT_ROOT/.env" \
    -f "$COMPOSE_FILE" \
    -f "$COMPOSE_OVERRIDE" \
    logs $FOLLOW_FLAG "$@"
