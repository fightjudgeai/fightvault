// ─── Enums ────────────────────────────────────────────────────────────────────

export enum WeightClass {
  Strawweight = 'strawweight',
  Flyweight = 'flyweight',
  Bantamweight = 'bantamweight',
  Featherweight = 'featherweight',
  Lightweight = 'lightweight',
  Welterweight = 'welterweight',
  Middleweight = 'middleweight',
  LightHeavyweight = 'light_heavyweight',
  Heavyweight = 'heavyweight',
  SuperHeavyweight = 'super_heavyweight',
}

export enum FightingStyle {
  Boxer = 'boxer',
  Kickboxer = 'kickboxer',
  Wrestler = 'wrestler',
  BJJ = 'bjj',
  Muay_Thai = 'muay_thai',
  MMA = 'mma',
  Karate = 'karate',
  Taekwondo = 'taekwondo',
  Judo = 'judo',
  Sambo = 'sambo',
}

export enum FightResult {
  Win = 'win',
  Loss = 'loss',
  Draw = 'draw',
  NoContest = 'no_contest',
}

export enum WinMethod {
  KO = 'ko',
  TKO = 'tko',
  Submission = 'submission',
  Decision = 'decision',
  SplitDecision = 'split_decision',
  MajorityDecision = 'majority_decision',
  TechnicalDecision = 'technical_decision',
  DQ = 'dq',
  NoContest = 'no_contest',
}

export enum EventStatus {
  Upcoming = 'upcoming',
  Live = 'live',
  Completed = 'completed',
  Cancelled = 'cancelled',
}

export enum ConfidenceLevel {
  Low = 'low',
  Medium = 'medium',
  High = 'high',
}

// ─── Fighter ──────────────────────────────────────────────────────────────────

export interface Fighter {
  id: string
  name: string
  nickname?: string
  weight_class: WeightClass
  fighting_style: FightingStyle
  wins: number
  losses: number
  draws: number
  no_contests: number
  active: boolean
  gym?: string
  nationality?: string
  age?: number
  reach_inches?: number
  height_inches?: number
  created_at: string
  updated_at: string
}

export interface FighterCreate {
  name: string
  nickname?: string
  weight_class: WeightClass
  fighting_style: FightingStyle
  wins?: number
  losses?: number
  draws?: number
  no_contests?: number
  active?: boolean
  gym?: string
  nationality?: string
  age?: number
  reach_inches?: number
  height_inches?: number
}

export interface FighterCareerScore {
  fighter_id: string
  fighter_name: string
  fcs: number
  confidence: ConfidenceLevel
  fps_last_5_avg: number | null
  finish_threat: number
  volatility_score: number
  fights_scored: number
  computed_at: string
}

// ─── Event ────────────────────────────────────────────────────────────────────

export interface Event {
  id: string
  name: string
  date: string
  venue: string
  city: string
  state?: string
  country: string
  sanctioning_body?: string
  status: EventStatus
  bouts: Bout[]
  created_at: string
  updated_at: string
}

export interface EventCreate {
  name: string
  date: string
  venue: string
  city: string
  state?: string
  country?: string
  sanctioning_body?: string
  status?: EventStatus
}

// ─── Bout / Fight ─────────────────────────────────────────────────────────────

export interface Bout {
  id: string
  event_id: string
  bout_order: number
  fighter_a_id: string
  fighter_b_id: string
  fighter_a: Fighter
  fighter_b: Fighter
  weight_class: WeightClass
  scheduled_rounds: number
  result?: FightResult
  winner_id?: string
  win_method?: WinMethod
  end_round?: number
  end_time?: string
  is_title_fight: boolean
  is_main_event: boolean
  created_at: string
  updated_at: string
}

export interface BoutCreate {
  event_id: string
  bout_order: number
  fighter_a_id: string
  fighter_b_id: string
  weight_class: WeightClass
  scheduled_rounds?: number
  is_title_fight?: boolean
  is_main_event?: boolean
}

// ─── Round Stats ──────────────────────────────────────────────────────────────

export interface RoundStats {
  id: string
  bout_id: string
  round_number: number
  fighter_id: string
  significant_strikes_landed: number
  significant_strikes_attempted: number
  total_strikes_landed: number
  total_strikes_attempted: number
  takedowns_landed: number
  takedowns_attempted: number
  submission_attempts: number
  knockdowns: number
  control_time_seconds: number
  distance_strikes_landed: number
  clinch_strikes_landed: number
  ground_strikes_landed: number
}

export interface RoundStatsCreate {
  round_number: number
  fighter_id: string
  significant_strikes_landed: number
  significant_strikes_attempted: number
  total_strikes_landed: number
  total_strikes_attempted: number
  takedowns_landed?: number
  takedowns_attempted?: number
  submission_attempts?: number
  knockdowns?: number
  control_time_seconds?: number
  distance_strikes_landed?: number
  clinch_strikes_landed?: number
  ground_strikes_landed?: number
}

export interface FightResultSet {
  result: FightResult
  winner_id?: string
  win_method?: WinMethod
  end_round?: number
  end_time?: string
}

// ─── Scores ───────────────────────────────────────────────────────────────────

export interface RoundScore {
  round_number: number
  fighter_a_score: number
  fighter_b_score: number
  fighter_a_strikes_score: number
  fighter_b_strikes_score: number
  fighter_a_grappling_score: number
  fighter_b_grappling_score: number
  fighter_a_control_score: number
  fighter_b_control_score: number
  fighter_a_volume_score: number
  fighter_b_volume_score: number
}

export interface FightScore {
  bout_id: string
  fighter_a_id: string
  fighter_b_id: string
  fighter_a_name: string
  fighter_b_name: string
  fighter_a_fps: number
  fighter_b_fps: number
  fighter_a_total_score: number
  fighter_b_total_score: number
  rounds: RoundScore[]
  confidence: ConfidenceLevel
  computed_at: string
}

// ─── Matchmaking ──────────────────────────────────────────────────────────────

export interface MatchupScore {
  fighter_a_id: string
  fighter_b_id: string
  fighter_a_name: string
  fighter_b_name: string
  weight_class: WeightClass
  mms: number
  competitiveness_score: number
  action_potential_score: number
  style_clash_quality_balance: number
  finish_potential: number
  is_title_worthy: boolean
  explanation: string
  computed_at: string
}

export interface MatchupRecommendation {
  fighter_b_id: string
  fighter_b_name: string
  mms: number
  competitiveness_score: number
  action_potential_score: number
  style_clash_quality_balance: number
  is_title_worthy: boolean
}

export interface MatchmakingBoardEntry {
  fighter_a_id: string
  fighter_b_id: string
  fighter_a_name: string
  fighter_b_name: string
  weight_class: WeightClass
  mms: number
  competitiveness_score: number
  action_potential_score: number
  style_clash_quality_balance: number
  is_title_worthy: boolean
}

// ─── Reports ─────────────────────────────────────────────────────────────────

export interface IntelReport {
  id: string
  bout_id: string
  fighter_a_id: string
  fighter_b_id: string
  fighter_a_name: string
  fighter_b_name: string
  event_name?: string
  status: 'pending' | 'processing' | 'complete' | 'failed'
  narrative?: string
  strengths_a?: string
  weaknesses_a?: string
  strengths_b?: string
  weaknesses_b?: string
  prediction?: string
  key_factors?: string[]
  created_at: string
  updated_at: string
}

// ─── Pagination / Params ─────────────────────────────────────────────────────

export interface PaginationParams {
  skip?: number
  limit?: number
}

export interface EventsParams extends PaginationParams {
  status?: EventStatus
  search?: string
  date_from?: string
  date_to?: string
}

export interface FightersParams extends PaginationParams {
  search?: string
  weight_class?: WeightClass
  fighting_style?: FightingStyle
  active?: boolean
}

export interface MatchmakingBoardParams extends PaginationParams {
  weight_class?: WeightClass
  min_mms?: number
  title_worthy_only?: boolean
}

export interface ReportsParams extends PaginationParams {
  status?: string
}

export interface MatchupComputeRequest {
  fighter_a_id: string
  fighter_b_id: string
}

// ─── Leaderboard ─────────────────────────────────────────────────────────────

export interface EventLeaderboardEntry {
  bout_id: string
  fighter_id: string
  fighter_name: string
  fps: number
  confidence: ConfidenceLevel
}

// ─── Generic API responses ────────────────────────────────────────────────────

export interface ApiError {
  detail: string
}
