export interface Player {
  puuid: string;
  riot_id?: string;
  tag_line?: string;
  summoner_name: string;
  platform: string;
  account_level: number;
  profile_icon_id?: number;
  summoner_id?: string;
  created_at: string;
  updated_at: string;
  last_seen: string;
}

export interface Match {
  match_id: string;
  platform_id: string;
  game_creation: number;
  game_duration: number;
  queue_id: number;
  game_version: string;
  map_id: number;
  game_mode?: string;
  game_type?: string;
  game_end_timestamp?: number;
  tournament_id?: string;
  is_processed: boolean;
  processing_error?: string;
  created_at: string;
  updated_at: string;
  game_start_datetime?: string;
  game_end_datetime?: string;
  patch_version?: string;
  is_ranked_match: boolean;
  is_normal_match: boolean;
}

export interface MatchListResponse {
  matches: Match[];
  total: number;
  start: number;
  count: number;
}

export interface MatchStatsResponse {
  puuid: string;
  total_matches: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_kills: number;
  avg_deaths: number;
  avg_assists: number;
  avg_kda: number;
  avg_cs: number;
  avg_vision_score: number;
}

export interface MatchParticipant {
  id: number;
  match_id: string;
  puuid: string;
  summoner_name: string;
  team_id: number;
  champion_name: string;
  kills: number;
  deaths: number;
  assists: number;
  win: boolean;
  kda: number;
}

export interface DetectionFactor {
  name: string;
  value: number;
  meets_threshold: boolean;
  weight: number;
  description: string;
  score: number;
}

export interface DetectionResponse {
  puuid: string;
  is_smurf: boolean;
  detection_score: number;
  confidence_level: string;
  factors: DetectionFactor[];
  reason: string;
  sample_size: number;
  analysis_time_seconds?: number;
  created_at?: string;
}

export interface DetectionStatsResponse {
  total_analyses: number;
  smurf_count: number;
  smurf_detection_rate: number;
  average_score: number;
  confidence_distribution: Record<string, number>;
  factor_trigger_rates: Record<string, number>;
  queue_type_distribution: Record<string, number>;
  last_analysis?: string;
}

export interface DetectionConfigResponse {
  thresholds: Record<string, number>;
  weights: Record<string, number>;
  min_games_required: number;
  analysis_version: string;
  last_updated: string;
}

export interface DetectionRequest {
  puuid: string;
  min_games?: number;
  queue_filter?: number;
  time_period_days?: number;
  force_reanalyze?: boolean;
}
