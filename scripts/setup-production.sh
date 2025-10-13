#!/bin/bash

# Production Setup Script
# This script performs a complete production environment setup including:
# - Database reset (WARNING: deletes all data!)
# - Seeding job configurations
# - Seeding tracked players
# - Restarting backend to load configurations
#
# Usage:
#   ./scripts/setup-production.sh
#
# IMPORTANT: This script is DESTRUCTIVE - it will delete all existing data!
# Only use this for:
# - Initial production setup
# - After schema changes that require database reset
# - Recovery from database corruption
#
# For normal deployments (code-only changes), just push to GitHub.

set -e  # Exit on any error

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          Production Environment Setup Script                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "⚠️  WARNING: This script will DELETE ALL DATA in the database!"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "❌ Setup cancelled."
    exit 1
fi

# Determine which docker compose file to use
COMPOSE_FILE="docker-compose.prod.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
    COMPOSE_FILE="docker-compose.yml"
    echo "ℹ️  Using $COMPOSE_FILE (production file not found)"
fi

echo ""
echo "Using docker compose file: $COMPOSE_FILE"
echo ""

# Check if services are running
if ! docker compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
    echo "⚠️  Services are not running. Starting services..."
    docker compose -f "$COMPOSE_FILE" up -d
    echo "⏳ Waiting 15 seconds for services to start..."
    sleep 15
fi

# Step 1: Reset database
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  Resetting database (drop all tables and recreate)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker compose -f "$COMPOSE_FILE" exec backend uv run python -m app.init_db reset

if [ $? -eq 0 ]; then
    echo "✅ Database reset completed"
else
    echo "❌ Database reset failed"
    exit 1
fi

echo ""

# Step 2: Seed job configurations
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  Seeding job configurations..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
./scripts/seed-job-configs.sh

if [ $? -eq 0 ]; then
    echo "✅ Job configurations seeded"
else
    echo "❌ Failed to seed job configurations"
    exit 1
fi

echo ""

# Step 3: Seed tracked players
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  Seeding tracked players..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
./scripts/seed-dev-data.sh

if [ $? -eq 0 ]; then
    echo "✅ Tracked players seeded"
else
    echo "❌ Failed to seed tracked players"
    exit 1
fi

echo ""

# Step 4: Restart backend to reload configurations
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  Restarting backend service..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker compose -f "$COMPOSE_FILE" restart backend

if [ $? -eq 0 ]; then
    echo "✅ Backend restarted"
else
    echo "❌ Failed to restart backend"
    exit 1
fi

echo ""

# Step 5: Wait for services to be healthy
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  Waiting for services to be healthy..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sleep 10

# Check backend health
BACKEND_PORT=8000
if [[ "$COMPOSE_FILE" == *"prod"* ]]; then
    BACKEND_PORT=8086
fi

MAX_RETRIES=10
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -sf http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
        echo "✅ Backend is healthy"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "⏳ Waiting for backend... (attempt $RETRY_COUNT/$MAX_RETRIES)"
        sleep 2
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "⚠️  Backend health check timed out"
    echo "   Check logs: docker compose -f $COMPOSE_FILE logs backend"
fi

echo ""

# Step 6: Verify setup
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6️⃣  Verifying setup..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check database
echo ""
echo "📊 Database Status:"
docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U riot_api_user -d riot_api_db <<EOF
SELECT
    'Job Configurations' as table_name,
    COUNT(*) as count
FROM job_configurations
UNION ALL
SELECT
    'Tracked Players',
    COUNT(*)
FROM players WHERE is_tracked = true
UNION ALL
SELECT
    'Total Players',
    COUNT(*)
FROM players;
EOF

# Check job scheduler
echo ""
echo "🔧 Job Scheduler Status:"
if curl -sf http://localhost:$BACKEND_PORT/api/v1/jobs/status/overview | python3 -m json.tool 2>/dev/null; then
    echo "✅ Job scheduler is running"
else
    echo "⚠️  Could not retrieve job status"
fi

# Check services
echo ""
echo "🐳 Docker Services:"
docker compose -f "$COMPOSE_FILE" ps

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Production setup completed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Next Steps:"
echo "   • Monitor logs: docker compose -f $COMPOSE_FILE logs -f backend"
echo "   • Check health: curl http://localhost:$BACKEND_PORT/health"
echo "   • View jobs: curl http://localhost:$BACKEND_PORT/api/v1/jobs/status/overview"
echo ""
echo "⚠️  Note: Jobs will start running automatically every 2 minutes."
echo "   It may take a few minutes for match data to appear."
echo ""
