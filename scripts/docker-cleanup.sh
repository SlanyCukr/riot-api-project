#!/bin/bash

# Docker Cleanup Script for Riot API Project
# This script helps resolve port conflicts and clean up Docker resources

set -e

echo "🧹 Docker Cleanup Script for Riot API Project"
echo "=============================================="
echo ""

# Stop local PostgreSQL if running
echo "1. Checking for local PostgreSQL service..."
if sudo service postgresql status > /dev/null 2>&1; then
    echo "   ⚠️  Local PostgreSQL is running. Stopping it..."
    sudo service postgresql stop
    echo "   ✅ Local PostgreSQL stopped"
else
    echo "   ✅ Local PostgreSQL is not running"
fi

# Stop and remove all project containers
echo ""
echo "2. Stopping Docker Compose services..."
docker compose down 2>/dev/null || echo "   No running compose services found"

# Find and stop any orphaned containers
echo ""
echo "3. Checking for orphaned containers..."
ORPHANED=$(docker ps -a | grep -E 'riot_api|postgres.*5432' | awk '{print $1}' || true)
if [ ! -z "$ORPHANED" ]; then
    echo "   Found orphaned containers. Removing..."
    echo "$ORPHANED" | xargs docker rm -f
    echo "   ✅ Orphaned containers removed"
else
    echo "   ✅ No orphaned containers found"
fi

# Remove orphaned networks
echo ""
echo "4. Checking for orphaned networks..."
ORPHANED_NETWORKS=$(docker network ls | grep riot | awk '{print $1}' || true)
if [ ! -z "$ORPHANED_NETWORKS" ]; then
    echo "   Found orphaned networks. Removing..."
    echo "$ORPHANED_NETWORKS" | xargs docker network rm 2>/dev/null || true
    echo "   ✅ Orphaned networks removed"
else
    echo "   ✅ No orphaned networks found"
fi

# Check if ports are free
echo ""
echo "5. Verifying ports are free..."
PORT_CHECK=$(netstat -tuln | grep -E ':(3000|5432|8000)\s' || true)
if [ -z "$PORT_CHECK" ]; then
    echo "   ✅ All required ports (3000, 5432, 8000) are free"
else
    echo "   ⚠️  Some ports are still in use:"
    echo "$PORT_CHECK"
    echo ""
    echo "   You may need to manually stop the processes using these ports"
fi

echo ""
echo "=============================================="
echo "✅ Cleanup complete!"
echo ""
echo "You can now run: docker compose up -d"
echo ""
