import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Plus, Building2, X } from 'lucide-react'
import { getPromotions, createPromotion } from '../lib/api'
import type { PromotionCreate } from '../lib/types'

const EMPTY_FORM: PromotionCreate = {
  name: '',
  slug: '',
  city: '',
  state: '',
  country: 'US',
}

export default function Promotions() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState<PromotionCreate>(EMPTY_FORM)
  const [formError, setFormError] = useState<string | null>(null)

  const { data: promotions = [], isLoading } = useQuery({
    queryKey: ['promotions'],
    queryFn: () => getPromotions(),
  })

  const mutation = useMutation({
    mutationFn: createPromotion,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['promotions'] })
      setShowModal(false)
      setForm(EMPTY_FORM)
      setFormError(null)
    },
    onError: (err: Error) => setFormError(err.message),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.name || !form.slug) {
      setFormError('Name and slug are required.')
      return
    }
    mutation.mutate(form)
  }

  function autoSlug(name: string) {
    return name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div className="page-header mb-0">
          <h1 className="page-title">Promotions</h1>
          <p className="page-subtitle">Browse fighters by promotion</p>
        </div>
        <button className="btn-primary shrink-0" onClick={() => setShowModal(true)}>
          <Plus size={15} />
          Add Promotion
        </button>
      </div>

      {isLoading ? (
        <p className="text-text-muted text-sm">Loading promotions...</p>
      ) : promotions.length === 0 ? (
        <div className="card flex flex-col items-center justify-center py-16 text-center">
          <Building2 size={36} className="text-text-muted mb-3" />
          <p className="text-text-secondary text-sm font-medium">No promotions yet</p>
          <p className="text-text-muted text-xs mt-1">Add a promotion to start organizing fighters</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {promotions.map((p) => (
            <button
              key={p.id}
              onClick={() => navigate(`/promotions/${p.id}`)}
              className="card text-left hover:border-accent/50 transition-colors group"
            >
              <div className="flex items-start gap-3">
                {p.logo_url ? (
                  <img
                    src={p.logo_url}
                    alt={p.name}
                    className="w-10 h-10 rounded object-contain bg-surface shrink-0"
                  />
                ) : (
                  <div className="w-10 h-10 rounded bg-surface flex items-center justify-center shrink-0">
                    <Building2 size={18} className="text-text-muted" />
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  <p className="text-text-primary font-semibold text-sm group-hover:text-accent transition-colors truncate">
                    {p.name}
                  </p>
                  {(p.city || p.country) && (
                    <p className="text-text-muted text-xs mt-0.5">
                      {[p.city, p.state, p.country].filter(Boolean).join(', ')}
                    </p>
                  )}
                  {p.description && (
                    <p className="text-text-muted text-xs mt-1 line-clamp-2">{p.description}</p>
                  )}
                  <div className="flex gap-3 mt-2">
                    <span className="text-text-muted text-[11px]">
                      <span className="text-text-secondary font-medium">{p.fighter_count ?? 0}</span> fighters
                    </span>
                    {p.bout_count != null && p.bout_count > 0 && (
                      <span className="text-text-muted text-[11px]">
                        <span className="text-text-secondary font-medium">{p.bout_count}</span> bouts
                      </span>
                    )}
                  </div>
                </div>
                <span
                  className={`badge text-[10px] shrink-0 ${
                    p.active
                      ? 'bg-emerald-900/40 text-emerald-400'
                      : 'bg-zinc-700 text-text-muted'
                  }`}
                >
                  {p.active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Add Promotion Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70" onClick={() => setShowModal(false)} />
          <div className="relative bg-card border border-border rounded-lg w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <h2 className="text-text-primary font-semibold">Add Promotion</h2>
              <button className="text-text-muted hover:text-text-primary" onClick={() => setShowModal(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="px-5 py-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1.5">Name *</label>
                <input
                  className="input"
                  placeholder="e.g. Bellator MMA"
                  value={form.name}
                  onChange={(e) => {
                    const name = e.target.value
                    setForm({ ...form, name, slug: form.slug || autoSlug(name) })
                  }}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1.5">Slug *</label>
                <input
                  className="input font-mono text-xs"
                  placeholder="e.g. bellator-mma"
                  value={form.slug}
                  onChange={(e) => setForm({ ...form, slug: e.target.value })}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1.5">City</label>
                  <input
                    className="input"
                    placeholder="e.g. Los Angeles"
                    value={form.city ?? ''}
                    onChange={(e) => setForm({ ...form, city: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1.5">State</label>
                  <input
                    className="input"
                    placeholder="e.g. CA"
                    value={form.state ?? ''}
                    onChange={(e) => setForm({ ...form, state: e.target.value })}
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1.5">Website</label>
                <input
                  className="input"
                  placeholder="https://..."
                  value={form.website ?? ''}
                  onChange={(e) => setForm({ ...form, website: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1.5">Description</label>
                <textarea
                  className="input resize-none"
                  rows={2}
                  placeholder="Short description..."
                  value={form.description ?? ''}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </div>

              {formError && <p className="text-red-400 text-xs">{formError}</p>}

              <div className="flex justify-end gap-3 pt-1">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={mutation.isPending}>
                  {mutation.isPending ? 'Adding...' : 'Add Promotion'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
