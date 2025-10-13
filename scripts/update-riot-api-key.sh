#!/bin/bash

# Update Riot API Key Script
# This script updates the RIOT_API_KEY in .env and restarts the backend container
# to pick up the new key immediately.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the project root directory (parent of scripts directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

echo -e "${YELLOW}=== Riot API Key Update Script ===${NC}\n"

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: .env file not found at $ENV_FILE${NC}"
    echo "Please create one from .env.example first."
    exit 1
fi

# Prompt for new API key
echo -e "${YELLOW}Enter your new Riot API key:${NC}"
echo "(Get it from: https://developer.riotgames.com)"
read -r NEW_API_KEY

# Validate API key format (basic check)
if [[ ! "$NEW_API_KEY" =~ ^RGAPI-[a-zA-Z0-9\-]+$ ]]; then
    echo -e "${RED}Error: Invalid API key format. Should start with 'RGAPI-'${NC}"
    exit 1
fi

# Check if RIOT_API_KEY is set in host environment (takes precedence over .env)
if [ -n "${RIOT_API_KEY:-}" ]; then
    echo -e "${YELLOW}Warning: RIOT_API_KEY is set in your shell environment.${NC}"
    echo -e "${YELLOW}Host environment variables take precedence over .env file.${NC}"
    echo -e "${YELLOW}Updating environment variable for this session...${NC}\n"
    export RIOT_API_KEY="$NEW_API_KEY"
fi

# Update the API key in .env file
if grep -q "^RIOT_API_KEY=" "$ENV_FILE"; then
    # Replace existing key
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|^RIOT_API_KEY=.*|RIOT_API_KEY=$NEW_API_KEY|" "$ENV_FILE"
    else
        # Linux
        sed -i "s|^RIOT_API_KEY=.*|RIOT_API_KEY=$NEW_API_KEY|" "$ENV_FILE"
    fi
    echo -e "${GREEN}✓ Updated RIOT_API_KEY in .env file${NC}"
else
    # Add new key if it doesn't exist
    echo "RIOT_API_KEY=$NEW_API_KEY" >> "$ENV_FILE"
    echo -e "${GREEN}✓ Added RIOT_API_KEY to .env file${NC}"
fi

# Navigate to project root
cd "$PROJECT_ROOT"

# Restart backend container to pick up new environment variables
echo -e "${YELLOW}Restarting backend container to apply new API key...${NC}"

# Down and up backend to force re-reading .env
# This is the most reliable way to ensure environment variables are updated
docker compose down backend 2>/dev/null || true
docker compose up -d backend

echo -e "\n${YELLOW}Waiting for backend to be healthy...${NC}"
sleep 5

# Check backend status
MAX_WAIT=30
COUNTER=0
while [ $COUNTER -lt $MAX_WAIT ]; do
    if docker compose ps backend | grep -q "healthy"; then
        echo -e "${GREEN}✓ Backend is healthy and running!${NC}\n"

        # Verify the API key is loaded (show first 10 chars only)
        API_KEY_PREFIX=$(docker compose exec -T backend bash -c 'echo ${RIOT_API_KEY:0:10}' 2>/dev/null || echo "Unable to verify")
        echo -e "${GREEN}✓ API Key loaded (prefix): $API_KEY_PREFIX${NC}"

        echo -e "\n${GREEN}=== API Key Update Complete ===${NC}"
        echo -e "${YELLOW}Note: Development API keys expire every 24 hours.${NC}"
        echo -e "${YELLOW}Remember to update it daily if you're actively developing.${NC}\n"
        exit 0
    fi

    sleep 2
    COUNTER=$((COUNTER + 2))
    echo -n "."
done

echo -e "\n${YELLOW}Warning: Backend started but health check is taking longer than expected.${NC}"
echo "Check logs with: docker compose logs backend"
echo -e "${GREEN}API key should still be updated.${NC}\n"
