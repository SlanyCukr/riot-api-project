#!/bin/bash

# Seed development data into the database
# This script inserts test player data for development and testing purposes
#
# Usage:
#   ./scripts/seed-dev-data.sh

set -e

echo "🌱 Seeding development data..."

# Get database connection details from .env or use defaults
POSTGRES_USER=${POSTGRES_USER:-riot_api_user}
POSTGRES_DB=${POSTGRES_DB:-riot_api_db}

# 3LosingLanes#AGAIN - Friend's account to track
# PUUID: Wv8Jx8FgJp-an8egCuGyoOIMKcWPgeqtH4CXhBWa-bbLA1f2HhHdOf1aQuhgZllIta6ddQLS3AUX0w
# Platform: EUN1

docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<EOF
-- Insert 3LosingLanes as tracked player (for automated updates)
INSERT INTO players (
    puuid,
    riot_id,
    tag_line,
    summoner_name,
    platform,
    is_active,
    is_tracked,
    is_analyzed
)
VALUES (
    'Wv8Jx8FgJp-an8egCuGyoOIMKcWPgeqtH4CXhBWa-bbLA1f2HhHdOf1aQuhgZllIta6ddQLS3AUX0w',
    '3LosingLanes',
    'AGAIN',
    '3LosingLanes',
    'eun1',
    true,
    true,
    false
)
ON CONFLICT (puuid) DO UPDATE SET
    riot_id = EXCLUDED.riot_id,
    tag_line = EXCLUDED.tag_line,
    summoner_name = EXCLUDED.summoner_name,
    platform = EXCLUDED.platform,
    is_tracked = EXCLUDED.is_tracked,
    is_analyzed = EXCLUDED.is_analyzed,
    updated_at = NOW();

-- Display seeded players
SELECT
    summoner_name,
    riot_id,
    tag_line,
    is_tracked,
    is_analyzed,
    account_level,
    puuid
FROM players
WHERE puuid = 'Wv8Jx8FgJp-an8egCuGyoOIMKcWPgeqtH4CXhBWa-bbLA1f2HhHdOf1aQuhgZllIta6ddQLS3AUX0w';
EOF

if [ $? -eq 0 ]; then
    echo "✅ Development data seeded successfully!"
    echo ""
    echo "Tracked player added:"
    echo "  • 3LosingLanes#AGAIN (EUN1)"
    echo "    PUUID: Wv8Jx8FgJp-an8egCuGyoOIMKcWPgeqtH4CXhBWa-bbLA1f2HhHdOf1aQuhgZllIta6ddQLS3AUX0w"
    echo "    Status: is_tracked=true, is_analyzed=false"
    echo ""
else
    echo "❌ Failed to seed development data"
    exit 1
fi
