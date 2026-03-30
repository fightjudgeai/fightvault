import clsx from 'clsx'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { ConfidenceLevel } from '../lib/types'
import ConfidenceBadge from './ConfidenceBadge'

interface ScoreCardProps {
  label: string
  value: string | number
  confidence?: ConfidenceLevel | string
  subtitle?: string
  trend?: 'up' | 'down' | 'flat'
  className?: string
  accentValue?: boolean
}

export default function ScoreCard({
  label,
  value,
  confidence,
  subtitle,
  trend,
  className,
  accentValue = false,
}: ScoreCardProps) {
  return (
    <div className={clsx('card p-4', className)}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="text-text-muted text-xs font-medium uppercase tracking-wider leading-none">
          {label}
        </p>
        {confidence && <ConfidenceBadge level={confidence} />}
      </div>

      <div className="flex items-end gap-2">
        <p
          className={clsx(
            'text-2xl font-semibold leading-none tabular-nums',
            accentValue ? 'text-accent' : 'text-text-primary',
          )}
        >
          {value}
        </p>
        {trend && (
          <span
            className={clsx(
              'mb-0.5',
              trend === 'up' && 'text-emerald-400',
              trend === 'down' && 'text-red-400',
              trend === 'flat' && 'text-text-muted',
            )}
          >
            {trend === 'up' && <TrendingUp size={14} />}
            {trend === 'down' && <TrendingDown size={14} />}
            {trend === 'flat' && <Minus size={14} />}
          </span>
        )}
      </div>

      {subtitle && (
        <p className="text-text-muted text-xs mt-1.5 leading-snug">{subtitle}</p>
      )}
    </div>
  )
}
