import { useState, useMemo } from 'react'
import { ChevronUp, ChevronDown, ChevronsUpDown, Loader2 } from 'lucide-react'
import clsx from 'clsx'

export interface Column<T = Record<string, unknown>> {
  key: string
  header: string
  render?: (value: unknown, row: T) => React.ReactNode
  sortable?: boolean
  width?: string
  align?: 'left' | 'center' | 'right'
}

interface DataTableProps<T extends Record<string, unknown>> {
  columns: Column<T>[]
  data: T[]
  onRowClick?: (row: T) => void
  loading?: boolean
  emptyMessage?: string
  rowKey?: (row: T) => string
}

type SortDir = 'asc' | 'desc' | null

export default function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  onRowClick,
  loading = false,
  emptyMessage = 'No data to display.',
  rowKey,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<SortDir>(null)

  function handleSort(key: string) {
    if (sortKey !== key) {
      setSortKey(key)
      setSortDir('asc')
    } else if (sortDir === 'asc') {
      setSortDir('desc')
    } else {
      setSortKey(null)
      setSortDir(null)
    }
  }

  const sorted = useMemo(() => {
    if (!sortKey || !sortDir) return data
    return [...data].sort((a, b) => {
      const av = a[sortKey]
      const bv = b[sortKey]
      if (av === bv) return 0
      if (av === null || av === undefined) return 1
      if (bv === null || bv === undefined) return -1
      const cmp = String(av).localeCompare(String(bv), undefined, {
        numeric: true,
      })
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [data, sortKey, sortDir])

  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border">
            {columns.map((col) => (
              <th
                key={col.key}
                className={clsx(
                  'px-4 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider whitespace-nowrap',
                  col.sortable && 'cursor-pointer select-none hover:text-text-secondary transition-colors',
                  col.align === 'right' && 'text-right',
                  col.align === 'center' && 'text-center',
                )}
                style={col.width ? { width: col.width } : undefined}
                onClick={() => col.sortable && handleSort(col.key)}
              >
                <span className="inline-flex items-center gap-1">
                  {col.header}
                  {col.sortable && (
                    <span className="text-text-muted">
                      {sortKey === col.key && sortDir === 'asc' ? (
                        <ChevronUp size={12} />
                      ) : sortKey === col.key && sortDir === 'desc' ? (
                        <ChevronDown size={12} />
                      ) : (
                        <ChevronsUpDown size={12} className="opacity-40" />
                      )}
                    </span>
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <tr key={i} className="border-b border-border">
                {columns.map((col) => (
                  <td key={col.key} className="px-4 py-3">
                    <div className="skeleton h-4 rounded w-24" />
                  </td>
                ))}
              </tr>
            ))
          ) : sorted.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-12 text-center text-text-muted text-sm"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            sorted.map((row, idx) => (
              <tr
                key={rowKey ? rowKey(row) : idx}
                onClick={() => onRowClick?.(row)}
                className={clsx(
                  'border-b border-border transition-colors',
                  onRowClick
                    ? 'cursor-pointer hover:bg-card'
                    : 'hover:bg-zinc-900/30',
                )}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={clsx(
                      'px-4 py-3 text-text-secondary whitespace-nowrap',
                      col.align === 'right' && 'text-right',
                      col.align === 'center' && 'text-center',
                    )}
                  >
                    {col.render
                      ? col.render(row[col.key], row)
                      : (row[col.key] as React.ReactNode) ?? (
                          <span className="text-text-muted">—</span>
                        )}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>

      {loading && (
        <div className="flex justify-center py-4 text-text-muted">
          <Loader2 size={16} className="animate-spin" />
        </div>
      )}
    </div>
  )
}
