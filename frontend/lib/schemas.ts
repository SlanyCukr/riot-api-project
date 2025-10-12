import { z } from "zod";

// Player Schema
export const PlayerSchema = z.object({
  puuid: z.string(),
  riot_id: z.string().optional(),
  tag_line: z.string().optional(),
  summoner_name: z.string(),
  platform: z.string(),
  account_level: z.number().int(),
  profile_icon_id: z.number().optional(),
  summoner_id: z.string().optional(),
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
  game_mode: z.string().optional(),
  game_type: z.string().optional(),
  game_end_timestamp: z.number().optional(),
  tournament_id: z.string().optional(),
  is_processed: z.boolean(),
  processing_error: z.string().optional(),
  created_at: z.string(),
  updated_at: z.string(),
  game_start_datetime: z.string().optional(),
  game_end_datetime: z.string().optional(),
  patch_version: z.string().optional(),
  is_ranked_match: z.boolean(),
  is_normal_match: z.boolean(),
});

// Match List Response Schema
export const MatchListResponseSchema = z.object({
  matches: z.array(MatchSchema),
  total: z.number(),
  start: z.number(),
  count: z.number(),
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
