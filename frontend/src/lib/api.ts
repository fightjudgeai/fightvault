import axios from 'axios'
import type {
  Fighter,
  FighterCreate,
  FighterCareerScore,
  Event,
  EventCreate,
  Bout,
  BoutCreate,
  RoundStatsCreate,
  FightResultSet,
  FightScore,
  MatchupScore,
  MatchupRecommendation,
  MatchmakingBoardEntry,
  IntelReport,
  EventsParams,
  FightersParams,
  MatchmakingBoardParams,
  ReportsParams,
  MatchupComputeRequest,
  EventLeaderboardEntry,
} from './types'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail ?? err.message ?? 'An unexpected error occurred'
    return Promise.reject(new Error(message))
  },
)

// ─── Events ──────────────────────────────────────────────────────────────────

export async function getEvents(params?: EventsParams): Promise<Event[]> {
  const { data } = await apiClient.get<Event[]>('/events', { params })
  return data
}

export async function createEvent(payload: EventCreate): Promise<Event> {
  const { data } = await apiClient.post<Event>('/events', payload)
  return data
}

export async function getEvent(id: string): Promise<Event> {
  const { data } = await apiClient.get<Event>(`/events/${id}`)
  return data
}

export async function getEventFights(id: string): Promise<Bout[]> {
  const { data } = await apiClient.get<Bout[]>(`/events/${id}/fights`)
  return data
}

export async function getEventLeaderboard(
  id: string,
): Promise<EventLeaderboardEntry[]> {
  const { data } = await apiClient.get<EventLeaderboardEntry[]>(
    `/events/${id}/leaderboard`,
  )
  return data
}

// ─── Fighters ────────────────────────────────────────────────────────────────

export async function getFighters(params?: FightersParams): Promise<Fighter[]> {
  const { data } = await apiClient.get<Fighter[]>('/fighters', { params })
  return data
}

export async function createFighter(payload: FighterCreate): Promise<Fighter> {
  const { data } = await apiClient.post<Fighter>('/fighters', payload)
  return data
}

export async function getFighter(id: string): Promise<Fighter> {
  const { data } = await apiClient.get<Fighter>(`/fighters/${id}`)
  return data
}

export async function getFighterScores(id: string): Promise<FightScore[]> {
  const { data } = await apiClient.get<FightScore[]>(`/fighters/${id}/scores`)
  return data
}

// ─── Fights / Bouts ──────────────────────────────────────────────────────────

export async function getFight(id: string): Promise<Bout> {
  const { data } = await apiClient.get<Bout>(`/fights/${id}`)
  return data
}

export async function createFight(payload: BoutCreate): Promise<Bout> {
  const { data } = await apiClient.post<Bout>('/fights', payload)
  return data
}

export async function submitRoundStats(
  fightId: string,
  payload: RoundStatsCreate,
): Promise<void> {
  await apiClient.post(`/fights/${fightId}/rounds`, payload)
}

export async function setFightResult(
  fightId: string,
  payload: FightResultSet,
): Promise<Bout> {
  const { data } = await apiClient.patch<Bout>(
    `/fights/${fightId}/result`,
    payload,
  )
  return data
}

export async function getFightScores(id: string): Promise<FightScore> {
  const { data } = await apiClient.get<FightScore>(`/fights/${id}/scores`)
  return data
}

// ─── Score Computation ───────────────────────────────────────────────────────

export async function computeFightScore(fightId: string): Promise<FightScore> {
  const { data } = await apiClient.post<FightScore>(
    `/scores/fight/${fightId}/compute`,
  )
  return data
}

export async function computeFighterScore(
  fighterId: string,
): Promise<FighterCareerScore> {
  const { data } = await apiClient.post<FighterCareerScore>(
    `/scores/fighter/${fighterId}/compute`,
  )
  return data
}

export async function getFighterScore(
  fighterId: string,
): Promise<FighterCareerScore> {
  const { data } = await apiClient.get<FighterCareerScore>(
    `/scores/fighter/${fighterId}`,
  )
  return data
}

// ─── Matchmaking ─────────────────────────────────────────────────────────────

export async function computeMatchup(
  payload: MatchupComputeRequest,
): Promise<MatchupScore> {
  const { data } = await apiClient.post<MatchupScore>(
    '/matchmaking/compute',
    payload,
  )
  return data
}

export async function getMatchupRecommendations(
  fighterId: string,
  params?: { limit?: number; weight_class?: string },
): Promise<MatchupRecommendation[]> {
  const { data } = await apiClient.get<MatchupRecommendation[]>(
    `/matchmaking/recommendations/${fighterId}`,
    { params },
  )
  return data
}

export async function getMatchmakingBoard(
  params?: MatchmakingBoardParams,
): Promise<MatchmakingBoardEntry[]> {
  const { data } = await apiClient.get<MatchmakingBoardEntry[]>(
    '/matchmaking/board',
    { params },
  )
  return data
}

// ─── Intel Reports ───────────────────────────────────────────────────────────

export async function generateIntelReport(
  fightId: string,
): Promise<IntelReport> {
  const { data } = await apiClient.post<IntelReport>(
    `/reports/generate/${fightId}`,
  )
  return data
}

export async function getReport(id: string): Promise<IntelReport> {
  const { data } = await apiClient.get<IntelReport>(`/reports/${id}`)
  return data
}

export async function getReports(
  params?: ReportsParams,
): Promise<IntelReport[]> {
  const { data } = await apiClient.get<IntelReport[]>('/reports', { params })
  return data
}
