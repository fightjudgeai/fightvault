import clsx from 'clsx'
import { ConfidenceLevel } from '../lib/types'

interface ConfidenceBadgeProps {
  level: ConfidenceLevel | string
  className?: string
}

const CONFIG: Record<string, { label: string; classes: string }> = {
  [ConfidenceLevel.High]: {
    label: 'High',
    classes: 'bg-emerald-900/40 text-emerald-400 border border-emerald-800/50',
  },
  [ConfidenceLevel.Medium]: {
    label: 'Medium',
    classes: 'bg-blue-900/40 text-blue-400 border border-blue-800/50',
  },
  [ConfidenceLevel.Low]: {
    label: 'Low',
    classes: 'bg-amber-900/40 text-amber-400 border border-amber-800/50',
  },
}

export default function ConfidenceBadge({
  level,
  className,
}: ConfidenceBadgeProps) {
  const config = CONFIG[level] ?? {
    label: level,
    classes: 'bg-zinc-800 text-text-muted border border-border',
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium tracking-wide uppercase',
        config.classes,
        className,
      )}
    >
      {config.label}
    </span>
  )
}
