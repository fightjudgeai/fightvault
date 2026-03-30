import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Plus, Search, X } from 'lucide-react'
import { getFighters, createFighter } from '../lib/api'
import { WeightClass, FightingStyle, FighterCreate } from '../lib/types'
import DataTable, { Column } from '../components/DataTable'

const EMPTY_FORM: FighterCreate = {
  name: '',
  nickname: '',
  weight_class: WeightClass.Lightweight,
  fighting_style: FightingStyle.MMA,
  wins: 0,
  losses: 0,
  draws: 0,
  no_contests: 0,
  active: true,
  gym: '',
  nationality: '',
}

export default function Fighters() {
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [search, setSearch] = useState('')
  const [weightFilter, setWeightFilter] = useState<WeightClass | ''>('')
  const [styleFilter, setStyleFilter] = useState<FightingStyle | ''>('')
  const [activeFilter, setActiveFilter] = useState<'all' | 'active' | 'inactive'>('all')
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState<FighterCreate>(EMPTY_FORM)
  const [formError, setFormError] = useState<string | null>(null)

  const { data: fighters = [], isLoading } = useQuery({
    queryKey: ['fighters', weightFilter, styleFilter, activeFilter],
    queryFn: () =>
      getFighters({
        limit: 500,
        weight_class: weightFilter || undefined,
        fighting_style: styleFilter || undefined,
        active:
          activeFilter === 'active'
            ? true
            : activeFilter === 'inactive'
            ? false
            : undefined,
      }),
  })

  const mutation = useMutation({
    mutationFn: createFighter,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['fighters'] })
      setShowModal(false)
      setForm(EMPTY_FORM)
      setFormError(null)
    },
    onError: (err: Error) => setFormError(err.message),
  })

  const filtered = fighters.filter((f) =>
    f.name.toLowerCase().includes(search.toLowerCase()) ||
    (f.nickname ?? '').toLowerCase().includes(search.toLowerCase()),
  )

  type FighterRow = (typeof filtered)[number] & Record<string, unknown>

  const columns: Column<FighterRow>[] = [
    {
      key: 'name',
      header: 'Fighter',
      sortable: true,
      render: (_, row) => (
        <div>
          <p className="text-text-primary font-medium">{row.name}</p>
          {row.nickname && (
            <p className="text-text-muted text-xs mt-0.5">"{row.nickname}"</p>
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
          {(row.no_contests as number) > 0 && (
            <span className="text-text-muted"> ({row.no_contests} NC)</span>
          )}
        </span>
      ),
    },
    {
      key: 'fighting_style',
      header: 'Style',
      sortable: true,
      render: (val) => (
        <span className="capitalize text-text-muted text-xs">
          {(val as string).replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      key: 'active',
      header: 'Status',
      render: (val) => (
        <span
          className={`badge text-[10px] ${
            val
              ? 'bg-emerald-900/40 text-emerald-400'
              : 'bg-zinc-700 text-text-muted'
          }`}
        >
          {val ? 'Active' : 'Inactive'}
        </span>
      ),
    },
    {
      key: 'gym',
      header: 'Gym',
      render: (val) =>
        val ? (
          <span className="text-text-muted text-xs">{val as string}</span>
        ) : (
          <span className="text-text-muted">—</span>
        ),
    },
  ]

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.name) {
      setFormError('Fighter name is required.')
      return
    }
    mutation.mutate(form)
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div className="page-header mb-0">
          <h1 className="page-title">Fighters</h1>
          <p className="page-subtitle">Fighter database and career records</p>
        </div>
        <button className="btn-primary shrink-0" onClick={() => setShowModal(true)}>
          <Plus size={15} />
          Add Fighter
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none"
          />
          <input
            className="input pl-8 w-56"
            placeholder="Search fighters..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
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
          className="select w-40"
          value={styleFilter}
          onChange={(e) => setStyleFilter(e.target.value as FightingStyle | '')}
        >
          <option value="">All Styles</option>
          {Object.values(FightingStyle).map((s) => (
            <option key={s} value={s} className="capitalize">
              {s.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
        <select
          className="select w-32"
          value={activeFilter}
          onChange={(e) =>
            setActiveFilter(e.target.value as 'all' | 'active' | 'inactive')
          }
        >
          <option value="all">All</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>

      <div className="card">
        <DataTable
          columns={columns as Column<Record<string, unknown>>[]}
          data={filtered as Record<string, unknown>[]}
          onRowClick={(row) => navigate(`/fighters/${row.id}`)}
          loading={isLoading}
          emptyMessage="No fighters found. Add fighters to your roster."
          rowKey={(row) => row.id as string}
        />
      </div>

      {/* Add Fighter Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/70"
            onClick={() => setShowModal(false)}
          />
          <div className="relative bg-card border border-border rounded-lg w-full max-w-lg shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border sticky top-0 bg-card">
              <h2 className="text-text-primary font-semibold">Add Fighter</h2>
              <button
                className="text-text-muted hover:text-text-primary"
                onClick={() => setShowModal(false)}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="px-5 py-4 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-text-secondary mb-1.5">
                    Full Name *
                  </label>
                  <input
                    className="input"
                    placeholder="e.g. Marcus Thompson"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-text-secondary mb-1.5">
                    Nickname
                  </label>
                  <input
                    className="input"
                    placeholder='e.g. "The Machine"'
                    value={form.nickname ?? ''}
                    onChange={(e) =>
                      setForm({ ...form, nickname: e.target.value })
                    }
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1.5">
                    Weight Class *
                  </label>
                  <select
                    className="select"
                    value={form.weight_class}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        weight_class: e.target.value as WeightClass,
                      })
                    }
                  >
                    {Object.values(WeightClass).map((w) => (
                      <option key={w} value={w} className="capitalize">
                        {w.replace(/_/g, ' ')}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1.5">
                    Fighting Style *
                  </label>
                  <select
                    className="select"
                    value={form.fighting_style}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        fighting_style: e.target.value as FightingStyle,
                      })
                    }
                  >
                    {Object.values(FightingStyle).map((s) => (
                      <option key={s} value={s} className="capitalize">
                        {s.replace(/_/g, ' ')}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-3">
                {(['wins', 'losses', 'draws', 'no_contests'] as const).map(
                  (field) => (
                    <div key={field}>
                      <label className="block text-xs font-medium text-text-secondary mb-1.5 capitalize">
                        {field.replace('_', ' ')}
                      </label>
                      <input
                        type="number"
                        min="0"
                        className="input"
                        value={form[field] ?? 0}
                        onChange={(e) =>
                          setForm({
                            ...form,
                            [field]: parseInt(e.target.value) || 0,
                          })
                        }
                      />
                    </div>
                  ),
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1.5">
                    Gym / Team
                  </label>
                  <input
                    className="input"
                    placeholder="e.g. American Top Team"
                    value={form.gym ?? ''}
                    onChange={(e) => setForm({ ...form, gym: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1.5">
                    Nationality
                  </label>
                  <input
                    className="input"
                    placeholder="e.g. USA"
                    value={form.nationality ?? ''}
                    onChange={(e) =>
                      setForm({ ...form, nationality: e.target.value })
                    }
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1.5">
                    Age
                  </label>
                  <input
                    type="number"
                    min="18"
                    max="60"
                    className="input"
                    value={form.age ?? ''}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        age: e.target.value ? parseInt(e.target.value) : undefined,
                      })
                    }
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1.5">
                    Reach (inches)
                  </label>
                  <input
                    type="number"
                    min="50"
                    max="90"
                    className="input"
                    value={form.reach_inches ?? ''}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        reach_inches: e.target.value
                          ? parseInt(e.target.value)
                          : undefined,
                      })
                    }
                  />
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="active"
                  checked={form.active ?? true}
                  onChange={(e) => setForm({ ...form, active: e.target.checked })}
                  className="accent-amber-500"
                />
                <label htmlFor="active" className="text-sm text-text-secondary">
                  Active fighter
                </label>
              </div>

              {formError && (
                <p className="text-red-400 text-xs">{formError}</p>
              )}

              <div className="flex justify-end gap-3 pt-1">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={mutation.isPending}
                >
                  {mutation.isPending ? 'Adding...' : 'Add Fighter'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
