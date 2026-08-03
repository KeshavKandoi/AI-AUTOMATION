import { cn } from '@/lib/utils'

interface BadgeProps {
  children: React.ReactNode
  tone?: 'signal' | 'alert' | 'amber' | 'neutral'
  className?: string
}

export default function Badge({ children, tone = 'neutral', className }: BadgeProps) {
  const toneClasses = {
    signal: 'text-[var(--color-signal)] bg-[var(--color-signal-dim)]',
    alert: 'text-[var(--color-alert)] bg-[var(--color-alert-dim)]',
    amber: 'text-[var(--color-amber)] bg-[var(--color-amber-dim)]',
    neutral: 'text-[var(--color-text-muted)] bg-[var(--color-surface-hover)]',
  }
  return (
    <span
      className={cn(
        'text-[10px] uppercase tracking-wide rounded px-2 py-1 shrink-0 inline-block',
        toneClasses[tone],
        className
      )}
    >
      {children}
    </span>
  )
}
