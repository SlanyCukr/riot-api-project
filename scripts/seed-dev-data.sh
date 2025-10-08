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

# Real player seed data for testing
# Jim Morioriarty#2434 from EUNE server (Level 794)
# PUUID fetched from Riot API on 2025-10-08

docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<EOF
INSERT INTO players (
    puuid,
    riot_id,
    tag_line,
    summoner_name,
    platform,
    account_level,
    is_active,
    profile_icon_id
)
VALUES (
    'Wv8Jx8FgJp-an8egCuGyoOIMKcWPgeqtH4CXhBWa-bbLA1f2HhHdOf1aQuhgZllIta6ddQLS3AUX0w',
    'Jim Morioriarty',
    '2434',
    'Jim Morioriarty',
    'eun1',
    794,
    true,
    6877
)
ON CONFLICT (puuid) DO UPDATE SET
    riot_id = EXCLUDED.riot_id,
    tag_line = EXCLUDED.tag_line,
    summoner_name = EXCLUDED.summoner_name,
    platform = EXCLUDED.platform,
    account_level = EXCLUDED.account_level,
    profile_icon_id = EXCLUDED.profile_icon_id,
    updated_at = NOW();
EOF

if [ $? -eq 0 ]; then
    echo "✅ Development data seeded successfully!"
    echo ""
    echo "Test player added:"
    echo "  Riot ID: Jim Morioriarty#2434"
    echo "  Platform: EUNE (eun1)"
    echo "  Level: 794"
else
    echo "❌ Failed to seed development data"
    exit 1
fi
