-- Initialize database for Riot API application
-- This script runs only once when the PostgreSQL container is first created

-- Enable pg_stat_statements for query performance monitoring
-- Note: requires shared_preload_libraries=pg_stat_statements in postgres command
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
