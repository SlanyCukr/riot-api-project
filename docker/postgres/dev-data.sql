-- Development data (only for development environment)
-- This file will be executed in development mode

-- Create test tables for development
CREATE TABLE IF NOT EXISTS app.players (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    puuid VARCHAR(78) UNIQUE NOT NULL,
    game_name VARCHAR(16) NOT NULL,
    tag_line VARCHAR(5) NOT NULL,
    region VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app.matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id VARCHAR(20) UNIQUE NOT NULL,
    game_mode VARCHAR(50) NOT NULL,
    game_duration INTEGER NOT NULL,
    game_creation BIGINT NOT NULL,
    region VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app TO ${POSTGRES_USER};
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA app TO ${POSTGRES_USER};