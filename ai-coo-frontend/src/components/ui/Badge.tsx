import { cn } from '@/lib/utils'

interface BadgeProps {
  children: React.ReactNode
  tone?: 'signal' | 'alert' | 'amber' | 'neutral'
  className?: string
}

export default function Badge({ children, tone = 'neutral', className }: BadgeProps) {
  const toneClasses = {
    signal: 'text-signal bg-signal-dim',
    alert: 'text-alert bg-alert-dim',
    amber: 'text-amber bg-amber-dim',
    neutral: 'text-text-muted bg-surface-hover',
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
