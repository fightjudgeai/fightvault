import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { getFighter, getFighterScore, getFighterScores } from '../lib/api'
import { FightResult, ConfidenceLevel } from '../lib/types'
import ScoreCard from '../components/ScoreCard'
import ConfidenceBadge from '../components/ConfidenceBadge'
import DataTable, { Column } from '../components/DataTable'
import clsx from 'clsx'

const RESULT_BADGE: Record<FightResult, { label: string; classes: string }> = {
  [FightResult.Win]: { label: 'W', classes: 'bg-emerald-900/40 text-emerald-400' },
  [FightResult.Loss]: { label: 'L', classes: 'bg-red-900/40 text-red-400' },
  [FightResult.Draw]: { label: 'D', classes: 'bg-amber-900/40 text-amber-400' },
  [FightResult.NoContest]: {
    label: 'NC',
    classes: 'bg-zinc-700 text-text-muted',
  },
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: Array<{ value: number }>
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-card border border-border rounded-md px-3 py-2 text-xs shadow-lg">
      <p className="text-text-muted mb-1">{label}</p>
      <p className="text-accent font-semibold">
        FPS: {payload[0].value.toFixed(1)}
      </p>
    </div>
  )
}

export default function FighterProfile() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: fighter, isLoading: fighterLoading } = useQuery({
    queryKey: ['fighter', id],
    queryFn: () => getFighter(id!),
    enabled: !!id,
  })

  const { data: careerScore, isLoading: scoreLoading } = useQuery({
    queryKey: ['fighter-score', id],
    queryFn: () => getFighterScore(id!),
    enabled: !!id,
    retry: false,
  })

  const { data: fightScores = [], isLoading: scoresLoading } = useQuery({
    queryKey: ['fighter-scores', id],
    queryFn: () => getFighterScores(id!),
    enabled: !!id,
  })

  if (fighterLoading) {
    return (
      <div className="space-y-4">
        <div className="skeleton h-6 w-48" />
        <div className="skeleton h-4 w-32" />
        <div className="grid grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-24 rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  if (!fighter) {
    return (
      <div className="text-center py-16 text-text-muted">
        Fighter not found.
        <button
          className="ml-2 text-accent hover:underline"
          onClick={() => navigate('/fighters')}
        >
          Back to fighters
        </button>
      </div>
    )
  }

  // Build FPS trend from last 5 fight scores
  const last5 = fightScores.slice(-5)
  const trendData = last5.map((s, i) => {
    const myFps =
      s.fighter_a_id === id ? s.fighter_a_fps : s.fighter_b_fps
    return {
      fight: `Fight ${i + 1}`,
      fps: myFps,
    }
  })

  type ScoreRow = (typeof fightScores)[number] & Record<string, unknown>

  const historyColumns: Column<ScoreRow>[] = [
    {
      key: 'fighter_a_name',
      header: 'Opponent',
      render: (_, row) => {
        const opponentName =
          row.fighter_a_id === id ? row.fighter_b_name : row.fighter_a_name
        const opponentId =
          row.fighter_a_id === id ? row.fighter_b_id : row.fighter_a_id
        return (
          <button
            className="text-text-primary hover:text-accent transition-colors"
            onClick={() => navigate(`/fighters/${opponentId as string}`)}
          >
            {opponentName as string}
          </button>
        )
      },
    },
    {
      key: 'computed_at',
      header: 'Date',
      render: (val) =>
        val
          ? new Date(val as string).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
            })
          : '—',
    },
    {
      key: 'fighter_a_fps',
      header: 'FPS',
      sortable: true,
      align: 'right',
      render: (_, row) => {
        const fps = row.fighter_a_id === id ? row.fighter_a_fps : row.fighter_b_fps
        return (
          <span className="text-accent font-semibold tabular-nums">
            {typeof fps === 'number' ? fps.toFixed(1) : '—'}
          </span>
        )
      },
    },
    {
      key: 'confidence',
      header: 'Confidence',
      render: (val) => <ConfidenceBadge level={val as ConfidenceLevel} />,
    },
  ]

  const fcs = careerScore?.fcs
  const fps5Avg = careerScore?.fps_last_5_avg
  const finishThreat = careerScore?.finish_threat
  const volatility = careerScore?.volatility_score

  return (
    <div className="space-y-6">
      {/* Back */}
      <button
        className="btn-ghost pl-0 text-text-muted"
        onClick={() => navigate('/fighters')}
      >
        <ArrowLeft size={14} />
        Fighters
      </button>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">
            {fighter.name}
            {fighter.nickname && (
              <span className="text-text-muted font-normal ml-2 text-base">
                "{fighter.nickname}"
              </span>
            )}
          </h1>
          <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-text-secondary">
            <span className="capitalize">
              {fighter.weight_class.replace(/_/g, ' ')}
            </span>
            <span className="text-border">·</span>
            <span className="capitalize">
              {fighter.fighting_style.replace(/_/g, ' ')}
            </span>
            <span className="text-border">·</span>
            <span className="font-medium tabular-nums">
              {fighter.wins}W-{fighter.losses}L-{fighter.draws}D
            </span>
            {fighter.gym && (
              <>
                <span className="text-border">·</span>
                <span className="text-text-muted">{fighter.gym}</span>
              </>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-3 mt-1.5 text-xs text-text-muted">
            {fighter.age && <span>Age {fighter.age}</span>}
            {fighter.reach_inches && <span>Reach {fighter.reach_inches}"</span>}
            {fighter.nationality && <span>{fighter.nationality}</span>}
            <span
              className={clsx(
                'badge',
                fighter.active
                  ? 'bg-emerald-900/40 text-emerald-400'
                  : 'bg-zinc-700 text-text-muted',
              )}
            >
              {fighter.active ? 'Active' : 'Inactive'}
            </span>
          </div>
        </div>
      </div>

      {/* Score cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <ScoreCard
          label="Fighter Career Score"
          value={
            scoreLoading
              ? '...'
              : fcs !== undefined
              ? fcs.toFixed(1)
              : 'N/A'
          }
          confidence={careerScore?.confidence}
          subtitle="FCS — overall career performance"
          accentValue={fcs !== undefined}
        />
        <ScoreCard
          label="FPS Last 5 Avg"
          value={
            scoreLoading
              ? '...'
              : fps5Avg !== null && fps5Avg !== undefined
              ? fps5Avg.toFixed(1)
              : 'N/A'
          }
          subtitle="Fight performance score average"
        />
        <ScoreCard
          label="Finish Threat"
          value={
            scoreLoading
              ? '...'
              : finishThreat !== undefined
              ? `${(finishThreat * 100).toFixed(0)}%`
              : 'N/A'
          }
          subtitle="Likelihood of finish"
        />
        <ScoreCard
          label="Volatility Score"
          value={
            scoreLoading
              ? '...'
              : volatility !== undefined
              ? volatility.toFixed(2)
              : 'N/A'
          }
          subtitle="Performance consistency"
        />
      </div>

      {/* Career score breakdown */}
      {careerScore && (
        <div>
          <h2 className="text-sm font-semibold text-text-primary uppercase tracking-wider mb-3">
            Career Score Breakdown
          </h2>
          <div className="card p-4">
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
              {[
                { label: 'Fights Scored', value: careerScore.fights_scored },
                {
                  label: 'FCS',
                  value: careerScore.fcs.toFixed(2),
                  accent: true,
                },
                {
                  label: 'FPS Last 5 Avg',
                  value:
                    careerScore.fps_last_5_avg !== null
                      ? careerScore.fps_last_5_avg.toFixed(2)
                      : '—',
                },
                {
                  label: 'Finish Threat',
                  value: `${(careerScore.finish_threat * 100).toFixed(1)}%`,
                },
                {
                  label: 'Volatility',
                  value: careerScore.volatility_score.toFixed(3),
                },
                {
                  label: 'Confidence',
                  value: (
                    <ConfidenceBadge level={careerScore.confidence} />
                  ) as unknown as string,
                },
                {
                  label: 'Computed At',
                  value: new Date(careerScore.computed_at).toLocaleString(),
                },
              ].map((item) => (
                <div key={item.label}>
                  <p className="text-text-muted text-xs uppercase tracking-wider mb-1">
                    {item.label}
                  </p>
                  <p
                    className={clsx(
                      'text-base font-semibold',
                      item.accent ? 'text-accent' : 'text-text-primary',
                    )}
                  >
                    {item.value}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* FPS Trend chart */}
      <div>
        <h2 className="text-sm font-semibold text-text-primary uppercase tracking-wider mb-3">
          FPS Trend — Last 5 Fights
        </h2>
        <div className="card p-4">
          {scoresLoading ? (
            <div className="skeleton h-40 rounded" />
          ) : trendData.length < 2 ? (
            <div className="h-40 flex items-center justify-center text-text-muted text-sm">
              Not enough scored fights to display trend.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <LineChart
                data={trendData}
                margin={{ top: 4, right: 16, bottom: 4, left: -20 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#23262d"
                  vertical={false}
                />
                <XAxis
                  dataKey="fight"
                  tick={{ fill: '#475569', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: '#475569', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<CustomTooltip />} />
                <Line
                  type="monotone"
                  dataKey="fps"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  dot={{ fill: '#f59e0b', r: 4, strokeWidth: 0 }}
                  activeDot={{ r: 5, fill: '#fbbf24' }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Fight history */}
      <div>
        <h2 className="text-sm font-semibold text-text-primary uppercase tracking-wider mb-3">
          Scored Fight History
        </h2>
        <div className="card">
          <DataTable
            columns={historyColumns as Column<Record<string, unknown>>[]}
            data={fightScores as Record<string, unknown>[]}
            loading={scoresLoading}
            emptyMessage="No scored fights on record yet."
            rowKey={(row) => row.bout_id as string}
          />
        </div>
      </div>
    </div>
  )
}
