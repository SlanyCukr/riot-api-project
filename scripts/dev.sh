#!/bin/bash

# Development Environment Launcher
# This script starts the development environment with Docker Compose Watch enabled.
# Features:
# - Hot reload for both frontend and backend
# - Automatic container recreation when .env changes
# - Development build targets with debug logging
# - Interactive logs from all services
#
# Usage:
#   ./scripts/dev.sh [OPTIONS] [SERVICE...]
#
# Options:
#   --build        Force rebuild of containers (uses Docker Bake)
#   --down         Stop all services first
#   --clean        Run docker-cleanup.sh before starting
#   --no-watch     Start without watch mode
#   --detach, -d   Run in detached mode (background)
#   --help, -h     Show this help message
#
# Database Management:
#   Use Alembic for all database changes:
#     docker compose exec backend uv run alembic upgrade head    # Apply migrations
#     docker compose exec backend uv run alembic revision --autogenerate -m "description"
#
# Examples:
#   ./scripts/dev.sh                    # Start all services with watch mode
#   ./scripts/dev.sh --build            # Rebuild and start with watch mode
#   ./scripts/dev.sh --clean            # Clean up Docker resources and start
#   ./scripts/dev.sh backend frontend   # Start only backend and frontend
#   ./scripts/dev.sh --no-watch         # Start without watch mode (just docker compose up)
#   ./scripts/dev.sh -d backend         # Start backend in background

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.yml"
COMPOSE_OVERRIDE="$PROJECT_ROOT/docker/docker-compose.override.yml"


# Docker compose command helper with both base and override files
docker_compose_cmd() {
    docker compose --env-file "$PROJECT_ROOT/.env" -f "$COMPOSE_FILE" -f "$COMPOSE_OVERRIDE" "$@"
}

# Parse arguments
FORCE_BUILD=false
STOP_FIRST=false
CLEAN_FIRST=false
USE_WATCH=true
DETACHED=false
SERVICES=()

show_help() {
    head -n 30 "$0" | grep "^#" | sed 's/^# //g' | sed 's/^#//g'
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            FORCE_BUILD=true
            shift
            ;;
        --down)
            STOP_FIRST=true
            shift
            ;;
        --clean)
            CLEAN_FIRST=true
            shift
            ;;
        --no-watch)
            USE_WATCH=false
            shift
            ;;
        --detach|-d)
            DETACHED=true
            shift
            ;;
        --help|-h)
            show_help
            ;;
        *)
            SERVICES+=("$1")
            shift
            ;;
    esac
done

# Header
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Development Environment - Docker Compose Watch          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Clean up if requested
if [ "$CLEAN_FIRST" = true ]; then
    echo -e "${YELLOW}🧹 Running Docker cleanup...${NC}"
    "$SCRIPT_DIR/docker-cleanup.sh"
    echo ""
fi

# Stop services if requested
if [ "$STOP_FIRST" = true ]; then
    echo -e "${YELLOW}⏹️  Stopping existing services...${NC}"
    cd "$PROJECT_ROOT"
    docker_compose_cmd down
    echo ""
fi

# Build if requested
if [ "$FORCE_BUILD" = true ]; then
    cd "$PROJECT_ROOT"

    echo -e "${YELLOW}🔨 Building containers with Docker Bake (parallel build)...${NC}"

    # Load .env file into shell environment for docker-bake
    if [ -f "$PROJECT_ROOT/.env" ]; then
        set -a  # Automatically export all variables
        source "$PROJECT_ROOT/.env"
        set +a
    fi

    # Export environment variables for Bake
    export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL}"
    export TAG="dev"

    # Build with Bake using dev group
    if [ ${#SERVICES[@]} -eq 0 ]; then
        docker buildx bake --allow=fs=/tmp -f docker/docker-bake.hcl dev --load
    else
        # Build specific services
        for service in "${SERVICES[@]}"; do
            docker buildx bake --allow=fs=/tmp -f docker/docker-bake.hcl "${service}-dev" --load
        done
    fi
    echo ""
fi

# Check if .env exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo -e "${YELLOW}   Please copy .env.example to .env and configure it${NC}"
    exit 1
fi

# Start services
cd "$PROJECT_ROOT"

if [ "$USE_WATCH" = true ]; then
    echo -e "${GREEN}🚀 Starting development environment with watch mode...${NC}"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✨ Features enabled:${NC}"
    echo -e "   ${GREEN}•${NC} Hot reload for code changes (both frontend and backend)"
    echo -e "   ${GREEN}•${NC} Automatic container recreation when .env changes"
    echo -e "   ${GREEN}•${NC} Debug logging enabled"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}💡 Tips:${NC}"
    echo -e "   ${YELLOW}•${NC} Save any .py file in backend/ → FastAPI auto-reloads"
    echo -e "   ${YELLOW}•${NC} Save any file in frontend/ → Next.js hot reloads"
    echo -e "   ${YELLOW}•${NC} Edit .env → containers automatically recreate"
    echo -e "   ${YELLOW}•${NC} Press Ctrl+C to stop all services"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [ "$DETACHED" = true ]; then
        # For detached mode, use regular up command instead of watch
        docker_compose_cmd up -d "${SERVICES[@]}"
        echo ""
        echo -e "${GREEN}✅ Services started in background${NC}"
        echo -e "${YELLOW}   Note: Using regular up command instead of watch for detached mode${NC}"
        echo -e "${YELLOW}   View logs: docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml logs -f${NC}"
        echo -e "${YELLOW}   Stop services: docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml down${NC}"
    else
        # Run in foreground with interactive logs using watch
        docker_compose_cmd watch "${SERVICES[@]}"
    fi
else
    echo -e "${GREEN}🚀 Starting development environment...${NC}"
    echo ""

    if [ "$DETACHED" = true ]; then
        docker_compose_cmd up -d "${SERVICES[@]}"
        echo ""
        echo -e "${GREEN}✅ Services started in background${NC}"
        echo -e "${YELLOW}   View logs: docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml logs -f${NC}"
        echo -e "${YELLOW}   Stop services: docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml down${NC}"
    else
        docker_compose_cmd up "${SERVICES[@]}"
    fi
fi
