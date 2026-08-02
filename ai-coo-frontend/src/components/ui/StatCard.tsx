import { motion } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: string | number
  icon: LucideIcon
  tone?: 'signal' | 'alert' | 'amber' | 'neutral'
  loading?: boolean
}

export default function StatCard({ label, value, icon: Icon, tone = 'neutral', loading }: StatCardProps) {
  const toneClasses = {
    signal: 'text-[var(--color-signal)] bg-[var(--color-signal-dim)]',
    alert: 'text-[var(--color-alert)] bg-[var(--color-alert-dim)]',
    amber: 'text-[var(--color-amber)] bg-[var(--color-amber-dim)]',
    neutral: 'text-[var(--color-text-muted)] bg-[var(--color-surface-hover)]',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60 backdrop-blur-xl p-5"
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-[var(--color-text-muted)]">{label}</span>
        <div className={cn('h-7 w-7 rounded-lg flex items-center justify-center', toneClasses[tone])}>
          <Icon size={14} />
        </div>
      </div>
      {loading ? (
        <div className="h-7 w-16 rounded bg-[var(--color-surface-hover)] animate-pulse" />
      ) : (
        <span className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
          {value}
        </span>
      )}
    </motion.div>
  )
}
