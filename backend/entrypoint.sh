#!/bin/bash
set -e

echo "============================================"
echo "Starting Riot API Backend Container"
echo "============================================"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "postgres" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is ready!"
echo ""

# Initialize database tables
echo "============================================"
echo "Initializing database tables..."
echo "============================================"
uv run python -m app.init_db init

# Check initialization exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "============================================"
    echo "Database initialization completed successfully!"
    echo "============================================"
    echo ""
else
    echo ""
    echo "============================================"
    echo "ERROR: Database initialization failed!"
    echo "============================================"
    exit 1
fi

# Seed job configurations (required for backend to function)
echo "============================================"
echo "Checking job configurations..."
echo "============================================"

JOB_CONFIG_COUNT=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "postgres" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
  "SELECT COUNT(*) FROM job_configurations" 2>/dev/null || echo "0")

if [ "$JOB_CONFIG_COUNT" -eq "0" ]; then
    echo "No job configurations found, seeding default configurations..."

    PGPASSWORD=$POSTGRES_PASSWORD psql -h "postgres" -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<EOF
-- Insert Tracked Player Updater Job Configuration
INSERT INTO job_configurations (
    job_type,
    name,
    schedule,
    is_active,
    config_json,
    created_at,
    updated_at
)
VALUES (
    'TRACKED_PLAYER_UPDATER',
    'Tracked Player Updater',
    'interval(seconds=120)',
    true,
    '{"max_new_matches_per_player": 50, "max_tracked_players": 20}'::jsonb,
    NOW(),
    NOW()
)
ON CONFLICT (name) DO UPDATE SET
    schedule = EXCLUDED.schedule,
    is_active = EXCLUDED.is_active,
    config_json = EXCLUDED.config_json,
    updated_at = NOW();

-- Insert Player Analyzer Job Configuration
INSERT INTO job_configurations (
    job_type,
    name,
    schedule,
    is_active,
    config_json,
    created_at,
    updated_at
)
VALUES (
    'PLAYER_ANALYZER',
    'Player Analyzer',
    'interval(seconds=120)',
    true,
    '{"discovered_players_per_run": 8, "matches_per_player_per_run": 10, "unanalyzed_players_per_run": 20, "ban_check_days": 7, "target_matches_per_player": 50}'::jsonb,
    NOW(),
    NOW()
)
ON CONFLICT (name) DO UPDATE SET
    schedule = EXCLUDED.schedule,
    is_active = EXCLUDED.is_active,
    config_json = EXCLUDED.config_json,
    updated_at = NOW();
EOF

    if [ $? -eq 0 ]; then
        echo "✅ Job configurations seeded successfully!"
        echo "   • Tracked Player Updater (runs every 2 minutes)"
        echo "   • Player Analyzer (runs every 2 minutes)"
    else
        echo "❌ Failed to seed job configurations"
        exit 1
    fi
else
    echo "Job configurations already exist (count: $JOB_CONFIG_COUNT), skipping seed"
fi

echo ""

# Start the application
echo "============================================"
echo "Starting application..."
echo "============================================"
echo ""
exec "$@"
