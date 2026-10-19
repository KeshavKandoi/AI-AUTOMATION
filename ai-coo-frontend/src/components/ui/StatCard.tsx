import { motion, useReducedMotion } from 'framer-motion'
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
  const reduceMotion = useReducedMotion()
  const toneClasses = {
    signal: 'text-signal bg-signal-dim',
    alert: 'text-alert bg-alert-dim',
    amber: 'text-amber bg-amber-dim',
    neutral: 'text-text-muted bg-surface-hover',
  }

  return (
    <motion.div
      variants={{ hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } }}
      initial={reduceMotion ? false : undefined}
      whileHover={reduceMotion ? undefined : { y: -3, borderColor: 'var(--color-border-hover)' }}
      transition={{ duration: reduceMotion ? 0 : 0.25, ease: 'easeOut' }}
      className="group relative overflow-hidden rounded-2xl border border-border bg-surface/75 p-5 shadow-[0_16px_44px_-34px_rgba(0,0,0,0.85)] backdrop-blur-xl transition-colors"
    >
      <div aria-hidden="true" className="pointer-events-none absolute inset-x-5 top-0 h-px bg-gradient-to-r from-transparent via-signal/45 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-text-muted">{label}</span>
        <div className={cn('h-7 w-7 rounded-lg flex items-center justify-center', toneClasses[tone])}>
          <Icon size={15} />
        </div>
      </div>
      {loading ? (
        <div className="h-7 w-16 rounded bg-surface-hover animate-pulse" />
      ) : (
        <span className="font-display text-2xl font-semibold text-text-primary">
          {value}
        </span>
      )}
    </motion.div>
  )
}
