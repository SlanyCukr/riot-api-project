#!/bin/bash

# Seed job configurations into the database
# This script creates default job configurations for the automated job system
#
# Usage:
#   ./scripts/seed-job-configs.sh

set -e

echo "🔧 Seeding job configurations..."

# Get database connection details from .env or use defaults
POSTGRES_USER=${POSTGRES_USER:-riot_api_user}
POSTGRES_DB=${POSTGRES_DB:-riot_api_db}

# Create default job configurations
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<EOF
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
    '{"max_new_matches_per_player": 20, "max_tracked_players": 10}'::jsonb,
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
    '{"unanalyzed_players_per_run": 5, "min_smurf_confidence": 0.5, "ban_check_days": 7}'::jsonb,
    NOW(),
    NOW()
)
ON CONFLICT (name) DO UPDATE SET
    schedule = EXCLUDED.schedule,
    is_active = EXCLUDED.is_active,
    config_json = EXCLUDED.config_json,
    updated_at = NOW();

-- Display created configurations
SELECT
    id,
    job_type,
    name,
    is_active,
    schedule,
    config_json
FROM job_configurations
ORDER BY id;
EOF

if [ $? -eq 0 ]; then
    echo "✅ Job configurations seeded successfully!"
    echo ""
    echo "Created job configurations:"
    echo "  1. Tracked Player Updater - Runs every 2 minutes"
    echo "  2. Player Analyzer - Runs every 2 minutes"
    echo ""
    echo "To manage jobs:"
    echo "  - View status: curl http://localhost:8000/api/v1/jobs/status/overview"
    echo "  - List jobs: curl http://localhost:8000/api/v1/jobs"
    echo "  - Enable/disable: Update 'is_active' in job_configurations table"
else
    echo "❌ Failed to seed job configurations"
    exit 1
fi
