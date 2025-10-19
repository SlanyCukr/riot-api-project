import { z } from "zod";

// Player Schema
export const PlayerSchema = z.object({
  puuid: z.string(),
  riot_id: z.string().optional().nullable(),
  tag_line: z.string().optional().nullable(),
  summoner_name: z.string(),
  platform: z.string(),
  account_level: z.number().int().optional().nullable(),
  profile_icon_id: z.number().optional().nullable(),
  summoner_id: z.string().optional().nullable(),
  id: z.number().optional().nullable(),
  is_tracked: z.boolean().optional().default(false),
  is_analyzed: z.boolean().optional().default(false),
  last_ban_check: z.string().optional().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
  last_seen: z.string(),
});

// Match Schema
export const MatchSchema = z.object({
  match_id: z.string(),
  platform_id: z.string(),
  game_creation: z.number(),
  game_duration: z.number(),
  queue_id: z.number(),
  game_version: z.string(),
  map_id: z.number(),
  game_mode: z.string().optional().nullable(),
  game_type: z.string().optional().nullable(),
  game_end_timestamp: z.number().optional().nullable(),
  tournament_id: z.string().optional().nullable(),
  is_processed: z.boolean(),
  processing_error: z.string().optional().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
  game_start_datetime: z.string().optional().nullable(),
  game_end_datetime: z.string().optional().nullable(),
  patch_version: z.string().optional().nullable(),
  is_ranked_match: z.boolean().optional(),
  is_normal_match: z.boolean().optional(),
});

// Match List Response Schema
export const MatchListResponseSchema = z.object({
  matches: z.array(MatchSchema),
  total: z.number(),
  page: z.number(),
  size: z.number(),
  pages: z.number(),
});

// Match Stats Response Schema
export const MatchStatsResponseSchema = z.object({
  puuid: z.string(),
  total_matches: z.number(),
  wins: z.number(),
  losses: z.number(),
  win_rate: z.number(),
  avg_kills: z.number(),
  avg_deaths: z.number(),
  avg_assists: z.number(),
  avg_kda: z.number(),
  avg_cs: z.number(),
  avg_vision_score: z.number(),
});

// Match Participant Schema
export const MatchParticipantSchema = z.object({
  id: z.number(),
  match_id: z.string(),
  puuid: z.string(),
  summoner_name: z.string(),
  team_id: z.number(),
  champion_name: z.string(),
  kills: z.number(),
  deaths: z.number(),
  assists: z.number(),
  win: z.boolean(),
  kda: z.number(),
});

// Detection Factor Schema
export const DetectionFactorSchema = z.object({
  name: z.string(),
  value: z.number(),
  meets_threshold: z.boolean(),
  weight: z.number(),
  description: z.string(),
  score: z.number(),
});

// Detection Response Schema
export const DetectionResponseSchema = z.object({
  puuid: z.string(),
  is_smurf: z.boolean(),
  detection_score: z.number(),
  confidence_level: z.string(),
  factors: z.array(DetectionFactorSchema),
  reason: z.string(),
  sample_size: z.number(),
  analysis_time_seconds: z.number().optional(),
  created_at: z.string().optional(),
});

// Detection Stats Response Schema
export const DetectionStatsResponseSchema = z.object({
  total_analyses: z.number(),
  smurf_count: z.number(),
  smurf_detection_rate: z.number(),
  average_score: z.number(),
  confidence_distribution: z.record(z.string(), z.number()),
  factor_trigger_rates: z.record(z.string(), z.number()),
  queue_type_distribution: z.record(z.string(), z.number()),
  last_analysis: z.string().optional(),
});

// Detection Config Response Schema
export const DetectionConfigResponseSchema = z.object({
  thresholds: z.record(z.string(), z.number()),
  weights: z.record(z.string(), z.number()),
  min_games_required: z.number(),
  analysis_version: z.string(),
  last_updated: z.string(),
});

// Detection Request Schema
export const DetectionRequestSchema = z.object({
  puuid: z.string(),
  min_games: z.number().int().min(1).optional().default(30),
  queue_filter: z.number().int().optional().default(420),
  time_period_days: z.number().int().optional(),
  force_reanalyze: z.boolean().optional().default(true),
});

// Infer TypeScript types from schemas
export type Player = z.infer<typeof PlayerSchema>;
export type Match = z.infer<typeof MatchSchema>;
export type MatchListResponse = z.infer<typeof MatchListResponseSchema>;
export type MatchStatsResponse = z.infer<typeof MatchStatsResponseSchema>;
export type MatchParticipant = z.infer<typeof MatchParticipantSchema>;
export type DetectionFactor = z.infer<typeof DetectionFactorSchema>;
export type DetectionResponse = z.infer<typeof DetectionResponseSchema>;
export type DetectionStatsResponse = z.infer<
  typeof DetectionStatsResponseSchema
>;
export type DetectionConfigResponse = z.infer<
  typeof DetectionConfigResponseSchema
>;
export type DetectionRequest = z.infer<typeof DetectionRequestSchema>;

// ===== JOB SCHEMAS =====

// Job Type Enum (must match backend enum values)
export const JobTypeSchema = z.enum([
  "tracked_player_updater",
  "player_analyzer",
]);

// Job Status Enum (must match backend enum values)
export const JobStatusSchema = z.enum([
  "pending",
  "running",
  "success",
  "failed",
]);

// Job Configuration Schema
export const JobConfigurationSchema = z.object({
  id: z.number(),
  job_type: JobTypeSchema,
  name: z.string(),
  schedule: z.string(),
  is_active: z.boolean(),
  config_json: z.record(z.string(), z.any()).nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

// Job Execution Schema
export const JobExecutionSchema = z.object({
  id: z.number(),
  job_config_id: z.number(),
  started_at: z.string(),
  completed_at: z.string().nullable().optional(),
  status: JobStatusSchema,
  api_requests_made: z.number().default(0),
  records_created: z.number().default(0),
  records_updated: z.number().default(0),
  error_message: z.string().nullable().optional(),
  execution_log: z.record(z.string(), z.any()).nullable().optional(),
  detailed_logs: z.record(z.string(), z.any()).nullable().optional(),
});

// Job Status Response Schema
export const JobStatusResponseSchema = z.object({
  scheduler_running: z.boolean(),
  active_jobs: z.number(),
  running_executions: z.number(),
  last_execution: JobExecutionSchema.nullable().optional(),
  next_run_time: z.string().nullable().optional(),
});

// Job Trigger Response Schema
export const JobTriggerResponseSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  execution_id: z.number().nullable().optional(),
});

// Job Execution List Response Schema
export const JobExecutionListResponseSchema = z.object({
  executions: z.array(JobExecutionSchema),
  total: z.number(),
  page: z.number(),
  size: z.number(),
  pages: z.number(),
});

// Infer TypeScript types for Jobs
export type JobType = z.infer<typeof JobTypeSchema>;
export type JobStatus = z.infer<typeof JobStatusSchema>;
export type JobConfiguration = z.infer<typeof JobConfigurationSchema>;
export type JobExecution = z.infer<typeof JobExecutionSchema>;
export type JobStatusResponse = z.infer<typeof JobStatusResponseSchema>;
export type JobTriggerResponse = z.infer<typeof JobTriggerResponseSchema>;
export type JobExecutionListResponse = z.infer<
  typeof JobExecutionListResponseSchema
>;

// Encounter Match Schema
export const EncounterMatchSchema = z.object({
  match_id: z.string(),
  summoner_name: z.string(),
  champion_name: z.string(),
  team_id: z.number(),
  is_teammate: z.boolean(),
  win: z.boolean(),
  kda: z.number(),
});

// Encounter Data Schema
export const EncounterDataSchema = z.object({
  total_encounters: z.number(),
  as_teammate: z.number(),
  as_opponent: z.number(),
  teammate_win_rate: z.number(),
  opponent_win_rate: z.number(),
  avg_kda: z.number(),
  recent_matches: z.array(EncounterMatchSchema),
});

// Encounter Stats Response Schema
export const EncounterStatsResponseSchema = z.object({
  puuid: z.string(),
  encounters: z.record(z.string(), EncounterDataSchema),
  total_unique_encounters: z.number(),
  matches_analyzed: z.number(),
});

// Detection Exists Response Schema
export const DetectionExistsResponseSchema = z.object({
  exists: z.boolean(),
  last_analysis: z.string().nullish(),
  is_smurf: z.boolean().nullish(),
  detection_score: z.number().nullish(),
  confidence_level: z.string().nullish(),
});

// Infer types
export type EncounterMatch = z.infer<typeof EncounterMatchSchema>;
export type EncounterData = z.infer<typeof EncounterDataSchema>;
export type EncounterStatsResponse = z.infer<
  typeof EncounterStatsResponseSchema
>;
export type DetectionExistsResponse = z.infer<
  typeof DetectionExistsResponseSchema
>;

// ===== RECENT OPPONENTS SCHEMA =====
// The backend returns a list of Player objects with full details
export const RecentOpponentsSchema = z.array(PlayerSchema);
export type RecentOpponents = z.infer<typeof RecentOpponentsSchema>;

// ===== PLAYER RANK SCHEMA =====
export const PlayerRankSchema = z.object({
  id: z.number(),
  puuid: z.string(),
  queue_type: z.string(),
  tier: z.string(),
  rank: z.string().nullable(),
  league_points: z.number(),
  wins: z.number(),
  losses: z.number(),
  veteran: z.boolean(),
  inactive: z.boolean(),
  fresh_blood: z.boolean(),
  hot_streak: z.boolean(),
  league_id: z.string().nullable(),
  league_name: z.string().nullable(),
  season_id: z.string().nullable(),
  is_current: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
  win_rate: z.number(),
  total_games: z.number(),
  display_rank: z.string(),
});

export type PlayerRank = z.infer<typeof PlayerRankSchema>;

// ===== SYSTEM SETTINGS SCHEMA =====
export const SettingSchema = z.object({
  key: z.string(),
  masked_value: z.string(),
  category: z.string(),
  is_sensitive: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const SettingUpdateSchema = z.object({
  value: z.string().min(1, "Value is required"),
});

export const SettingTestResponseSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  details: z.record(z.string(), z.any()).nullable().optional(),
});

export type Setting = z.infer<typeof SettingSchema>;
export type SettingUpdate = z.infer<typeof SettingUpdateSchema>;
export type SettingTestResponse = z.infer<typeof SettingTestResponseSchema>;
