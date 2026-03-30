import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Building2 } from 'lucide-react'
import { getPromotion, getPromotionFighters } from '../lib/api'
import { WeightClass } from '../lib/types'
import DataTable, { Column } from '../components/DataTable'
import ConfidenceBadge from '../components/ConfidenceBadge'

export default function PromotionDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [weightFilter, setWeightFilter] = useState<WeightClass | ''>('')
  const [activeFilter, setActiveFilter] = useState<'all' | 'active' | 'inactive'>('all')

  const { data: promotion, isLoading: promoLoading } = useQuery({
    queryKey: ['promotion', id],
    queryFn: () => getPromotion(id!),
    enabled: !!id,
  })

  const { data: fighters = [], isLoading: fightersLoading } = useQuery({
    queryKey: ['promotion-fighters', id, weightFilter, activeFilter],
    queryFn: () =>
      getPromotionFighters(id!, {
        weight_class: weightFilter || undefined,
        is_active: activeFilter === 'active' ? true : activeFilter === 'inactive' ? false : undefined,
        limit: 500,
      }),
    enabled: !!id,
  })

  type FighterRow = (typeof fighters)[number] & Record<string, unknown>

  const columns: Column<FighterRow>[] = [
    {
      key: 'name',
      header: 'Fighter',
      sortable: true,
      render: (_, row) => (
        <div>
          <p className="text-text-primary font-medium">
            {(row.first_name as string)} {(row.last_name as string)}
          </p>
          {row.nickname && (
            <p className="text-text-muted text-xs mt-0.5">"{row.nickname as string}"</p>
          )}
        </div>
      ),
    },
    {
      key: 'weight_class',
      header: 'Weight Class',
      sortable: true,
      render: (val) => (
        <span className="capitalize text-text-secondary text-sm">
          {(val as string).replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      key: 'wins',
      header: 'Record',
      render: (_, row) => (
        <span className="tabular-nums text-text-secondary text-sm font-medium">
          {row.wins as number}-{row.losses as number}-{row.draws as number}
        </span>
      ),
    },
    {
      key: 'fcs',
      header: 'FCS',
      sortable: true,
      render: (val, row) =>
        val != null ? (
          <div className="flex items-center gap-2">
            <span className="tabular-nums text-text-primary text-sm font-semibold">
              {Number(val).toFixed(1)}
            </span>
            {row.fcs_confidence && (
              <ConfidenceBadge level={row.fcs_confidence as string} />
            )}
          </div>
        ) : (
          <span className="text-text-muted text-xs">—</span>
        ),
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (val) => (
        <span
          className={`badge text-[10px] ${
            val ? 'bg-emerald-900/40 text-emerald-400' : 'bg-zinc-700 text-text-muted'
          }`}
        >
          {val ? 'Active' : 'Inactive'}
        </span>
      ),
    },
  ]

  if (promoLoading) {
    return <p className="text-text-muted text-sm">Loading...</p>
  }

  if (!promotion) {
    return <p className="text-red-400 text-sm">Promotion not found.</p>
  }

  return (
    <div className="space-y-5">
      {/* Back */}
      <button
        onClick={() => navigate('/promotions')}
        className="flex items-center gap-1.5 text-text-muted hover:text-text-primary text-sm transition-colors"
      >
        <ArrowLeft size={14} />
        All Promotions
      </button>

      {/* Header */}
      <div className="flex items-start gap-4">
        {promotion.logo_url ? (
          <img
            src={promotion.logo_url}
            alt={promotion.name}
            className="w-14 h-14 rounded object-contain bg-surface shrink-0"
          />
        ) : (
          <div className="w-14 h-14 rounded bg-surface flex items-center justify-center shrink-0">
            <Building2 size={22} className="text-text-muted" />
          </div>
        )}
        <div>
          <h1 className="page-title">{promotion.name}</h1>
          <p className="text-text-muted text-sm">
            {[promotion.city, promotion.state, promotion.country].filter(Boolean).join(', ')}
            {promotion.website && (
              <>
                {' · '}
                <a
                  href={promotion.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent hover:underline"
                >
                  Website
                </a>
              </>
            )}
          </p>
          {promotion.description && (
            <p className="text-text-secondary text-sm mt-1">{promotion.description}</p>
          )}
          <div className="flex gap-4 mt-2">
            <span className="text-text-muted text-xs">
              <span className="text-text-secondary font-medium">{promotion.fighter_count ?? fighters.length}</span> fighters
            </span>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          className="select w-44"
          value={weightFilter}
          onChange={(e) => setWeightFilter(e.target.value as WeightClass | '')}
        >
          <option value="">All Weight Classes</option>
          {Object.values(WeightClass).map((w) => (
            <option key={w} value={w} className="capitalize">
              {w.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
        <select
          className="select w-32"
          value={activeFilter}
          onChange={(e) => setActiveFilter(e.target.value as 'all' | 'active' | 'inactive')}
        >
          <option value="all">All</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>

      {/* Fighters table */}
      <div className="card">
        <DataTable
          columns={columns as Column<Record<string, unknown>>[]}
          data={fighters as Record<string, unknown>[]}
          onRowClick={(row) => navigate(`/fighters/${row.id}`)}
          loading={fightersLoading}
          emptyMessage="No fighters in this promotion."
          rowKey={(row) => row.id as string}
        />
      </div>
    </div>
  )
}
