-- Migration: Add is_tracked, is_analyzed, and last_ban_check columns to players table
-- Date: 2025-10-15
-- Description: Adds tracking and analysis flags to support automated background jobs

-- Add is_tracked column for automated player tracking
ALTER TABLE app.players ADD COLUMN IF NOT EXISTS is_tracked BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS ix_players_is_tracked ON app.players(is_tracked);
COMMENT ON COLUMN app.players.is_tracked IS 'Whether this player is being actively tracked for continuous updates';

-- Add is_analyzed column for smurf detection tracking
ALTER TABLE app.players ADD COLUMN IF NOT EXISTS is_analyzed BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS ix_players_is_analyzed ON app.players(is_analyzed);
COMMENT ON COLUMN app.players.is_analyzed IS 'Whether this player has been analyzed for smurf/boosted detection';

-- Add last_ban_check column for ban status tracking
ALTER TABLE app.players ADD COLUMN IF NOT EXISTS last_ban_check TIMESTAMP WITH TIME ZONE;
CREATE INDEX IF NOT EXISTS ix_players_last_ban_check ON app.players(last_ban_check);
COMMENT ON COLUMN app.players.last_ban_check IS 'When this player was last checked for ban status';
