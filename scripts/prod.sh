#!/bin/bash

# Production Environment Launcher
# This script starts the production environment with optimized settings.
# Features:
# - Production build targets with optimized performance
# - Resource limits and health checks
# - Automatic restarts on failure
# - Optional no-cache builds
#
# Usage:
#   ./scripts/prod.sh [OPTIONS] [SERVICE...]
#
# Options:
#   --build            Force rebuild of containers
#   --no-cache         Build without using cache (useful for deployments)
#   --down             Stop all services first
#   --reset-db         Wipe database and recreate from SQLAlchemy models (WARNING: deletes all data)
#   --logs, -f         Follow logs after starting
#   --detach, -d       Run in detached mode (default for production)
#   --help, -h         Show this help message
#
# Examples:
#   ./scripts/prod.sh                      # Start all services in production mode
#   ./scripts/prod.sh --build              # Rebuild and start production
#   ./scripts/prod.sh --no-cache --build   # Clean build (for deployments)
#   ./scripts/prod.sh --logs               # Start and follow logs
#   ./scripts/prod.sh backend              # Start only backend service

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
COMPOSE_PROD_FILE="$PROJECT_ROOT/docker/docker-compose.prod.yml"

# Parse arguments
FORCE_BUILD=false
NO_CACHE=false
STOP_FIRST=false
RESET_DB=false
FOLLOW_LOGS=false
DETACHED=true
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
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --down)
            STOP_FIRST=true
            shift
            ;;
        --reset-db)
            RESET_DB=true
            shift
            ;;
        --logs|-f)
            FOLLOW_LOGS=true
            DETACHED=false
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
echo -e "${BLUE}║         Production Environment - Docker Compose                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Stop services if requested
if [ "$STOP_FIRST" = true ]; then
    echo -e "${YELLOW}⏹️  Stopping existing services...${NC}"
    cd "$PROJECT_ROOT"
    docker compose --env-file "$PROJECT_ROOT/.env" -f "$COMPOSE_FILE" -f "$COMPOSE_PROD_FILE" down
    echo ""
fi

# Build if requested
if [ "$FORCE_BUILD" = true ]; then
    echo -e "${YELLOW}🔨 Building production containers...${NC}"
    cd "$PROJECT_ROOT"

    BUILD_ARGS=()
    if [ "$NO_CACHE" = true ]; then
        BUILD_ARGS+=("--no-cache")
        echo -e "${YELLOW}   Building without cache (this may take longer)...${NC}"
    fi

    docker compose --env-file "$PROJECT_ROOT/.env" -f "$COMPOSE_FILE" -f "$COMPOSE_PROD_FILE" build "${BUILD_ARGS[@]}" "${SERVICES[@]}"
    echo ""
fi

# Check if .env exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo -e "${YELLOW}   Please copy .env.example to .env and configure it${NC}"
    exit 1
fi

# Validate production environment variables
echo -e "${YELLOW}🔍 Validating environment...${NC}"
source "$PROJECT_ROOT/.env"

if [ -z "$RIOT_API_KEY" ]; then
    echo -e "${RED}❌ Error: RIOT_API_KEY not set in .env${NC}"
    exit 1
fi

if [ -z "$POSTGRES_PASSWORD" ]; then
    echo -e "${RED}❌ Error: POSTGRES_PASSWORD not set in .env${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment validated${NC}"
echo ""

# Reset database if requested
if [ "$RESET_DB" = true ]; then
    echo -e "${RED}⚠️  WARNING: This will DELETE ALL DATA in the production database!${NC}"
    read -p "Are you sure you want to reset the production database? (yes/no): " -r
    echo
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo -e "${YELLOW}Database reset cancelled. Continuing without reset...${NC}"
        echo ""
    else
        echo -e "${YELLOW}🗑️  Resetting production database...${NC}"

        # Stop services to ensure clean reset
        docker compose --env-file "$PROJECT_ROOT/.env" -f "$COMPOSE_FILE" -f "$COMPOSE_PROD_FILE" down -v

        # Start postgres to run reset
        docker compose --env-file "$PROJECT_ROOT/.env" -f "$COMPOSE_FILE" -f "$COMPOSE_PROD_FILE" up -d postgres
        echo "Waiting for postgres to be ready..."
        sleep 5

        # Start backend to run reset (entrypoint will recreate tables)
        docker compose --env-file "$PROJECT_ROOT/.env" -f "$COMPOSE_FILE" -f "$COMPOSE_PROD_FILE" up -d backend
        echo "Waiting for database reset to complete..."
        sleep 10

        # Stop backend after reset
        docker compose --env-file "$PROJECT_ROOT/.env" -f "$COMPOSE_FILE" -f "$COMPOSE_PROD_FILE" stop backend

        echo -e "${GREEN}✅ Database reset complete${NC}"
        echo ""
    fi
fi

# Start services
cd "$PROJECT_ROOT"

echo -e "${GREEN}🚀 Starting production environment...${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✨ Production features:${NC}"
echo -e "   ${GREEN}•${NC} Optimized build targets"
echo -e "   ${GREEN}•${NC} Resource limits and health checks"
echo -e "   ${GREEN}•${NC} Automatic restarts on failure"
echo -e "   ${GREEN}•${NC} Production logging level"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ "$DETACHED" = true ]; then
    docker compose --env-file "$PROJECT_ROOT/.env" -f "$COMPOSE_FILE" -f "$COMPOSE_PROD_FILE" up -d "${SERVICES[@]}"
    echo ""
    echo -e "${GREEN}✅ Production services started in background${NC}"
    echo ""
    echo -e "${YELLOW}📝 Useful commands:${NC}"
    echo -e "   ${YELLOW}•${NC} View logs: docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml logs -f"
    echo -e "   ${YELLOW}•${NC} Check status: docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml ps"
    echo -e "   ${YELLOW}•${NC} Stop services: docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml down"
    echo -e "   ${YELLOW}•${NC} View health: curl http://localhost:\${BACKEND_PORT}/health"
    echo ""

    # Wait a bit and show service status
    echo -e "${YELLOW}⏳ Waiting for services to start...${NC}"
    sleep 5
    echo ""
    docker compose --env-file "$PROJECT_ROOT/.env" -f "$COMPOSE_FILE" -f "$COMPOSE_PROD_FILE" ps

elif [ "$FOLLOW_LOGS" = true ]; then
    docker compose --env-file "$PROJECT_ROOT/.env" -f "$COMPOSE_FILE" -f "$COMPOSE_PROD_FILE" up "${SERVICES[@]}"
else
    docker compose --env-file "$PROJECT_ROOT/.env" -f "$COMPOSE_FILE" -f "$COMPOSE_PROD_FILE" up "${SERVICES[@]}"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Production environment is running${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
