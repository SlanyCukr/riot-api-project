-- Initialize database for Riot API application
-- This script runs only once when the PostgreSQL container is first created
--
-- Note: uuid-ossp extension removed - not needed since PUUIDs are stored as strings

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS app;

-- Set default privileges for the schema
-- Note: Using hardcoded user for compatibility with envsubst if needed later
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO riot_api_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT USAGE, SELECT ON SEQUENCES TO riot_api_user;

-- Set search path to include app schema
ALTER ROLE riot_api_user SET search_path TO app, public;

-- Grant permissions on database
GRANT ALL PRIVILEGES ON DATABASE riot_api_db TO riot_api_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO riot_api_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO riot_api_user;
