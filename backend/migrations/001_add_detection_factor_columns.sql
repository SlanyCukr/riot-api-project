-- Migration: Add missing detection factor columns to smurf_detections table
-- Date: 2025-10-17
-- Purpose: Store all 9 detection factors instead of just 4

-- Add the 5 missing detection factor score columns
ALTER TABLE smurf_detections
ADD COLUMN IF NOT EXISTS rank_progression_score NUMERIC(5, 3),
ADD COLUMN IF NOT EXISTS win_rate_trend_score NUMERIC(5, 3),
ADD COLUMN IF NOT EXISTS performance_consistency_score NUMERIC(5, 3),
ADD COLUMN IF NOT EXISTS performance_trends_score NUMERIC(5, 3),
ADD COLUMN IF NOT EXISTS role_performance_score NUMERIC(5, 3);

-- Add comments to new columns for documentation
COMMENT ON COLUMN smurf_detections.rank_progression_score IS 'Rank progression based smurf score component';
COMMENT ON COLUMN smurf_detections.win_rate_trend_score IS 'Win rate trend based smurf score component';
COMMENT ON COLUMN smurf_detections.performance_consistency_score IS 'Performance consistency based smurf score component';
COMMENT ON COLUMN smurf_detections.performance_trends_score IS 'Performance trends based smurf score component';
COMMENT ON COLUMN smurf_detections.role_performance_score IS 'Role performance based smurf score component';

-- Verify the columns were added
SELECT column_name, data_type, character_maximum_length, numeric_precision, numeric_scale
FROM information_schema.columns
WHERE table_name = 'smurf_detections'
  AND column_name IN (
    'rank_progression_score',
    'win_rate_trend_score',
    'performance_consistency_score',
    'performance_trends_score',
    'role_performance_score'
  )
ORDER BY column_name;
