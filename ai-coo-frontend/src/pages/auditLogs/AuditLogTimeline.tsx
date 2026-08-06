import { motion } from 'framer-motion'
import { formatDistanceToNow } from 'date-fns'
import type { AuditLogEntry } from '@/services/audit-logs'
import Badge from '@/components/ui/Badge'
import { getModuleIcon, getModuleLabel, getStatusTone, formatActionLabel } from '@/lib/auditLogDisplay'

interface AuditLogTimelineProps {
  logs: AuditLogEntry[]
  onSelect: (id: string) => void
}

const DOT_TONE_CLASS: Record<string, string> = {
  signal: 'bg-[var(--color-signal)]',
  alert: 'bg-[var(--color-alert)]',
  amber: 'bg-[var(--color-amber)]',
  neutral: 'bg-[var(--color-text-faint)]',
}

export default function AuditLogTimeline({ logs, onSelect }: AuditLogTimelineProps) {
  return (
    <div className="relative pl-2">
      <div className="absolute left-[15px] top-2 bottom-2 w-px bg-[var(--color-border)]" />
      <div className="flex flex-col gap-1">
        {logs.map((log, idx) => {
          const Icon = getModuleIcon(log.module)
          const tone = getStatusTone(log.status)
          return (
            <motion.button
              key={log.id}
              type="button"
              onClick={() => onSelect(log.id)}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: Math.min(idx, 10) * 0.02 }}
              className="relative flex items-start gap-4 py-3 pr-3 pl-1 text-left rounded-lg hover:bg-[var(--color-surface-hover)] transition-colors"
            >
              <span className="relative z-10 flex items-center justify-center h-7 w-7 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] shrink-0">
                <Icon size={13} className="text-[var(--color-text-muted)]" />
                <span
                  className={`absolute -right-0.5 -bottom-0.5 h-2 w-2 rounded-full ring-2 ring-[var(--color-surface)] ${DOT_TONE_CLASS[tone]}`}
                />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm text-[var(--color-text-primary)]">
                    {log.summary ?? formatActionLabel(log.action)}
                  </span>
                  <Badge tone={tone}>{log.status ?? 'info'}</Badge>
                </div>
                <div className="mt-0.5 flex items-center gap-2 text-xs text-[var(--color-text-faint)]">
                  <span>{getModuleLabel(log.module)}</span>
                  <span>·</span>
                  <span className="font-mono">{formatActionLabel(log.action)}</span>
                  <span>·</span>
                  <span>{formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}</span>
                </div>
              </div>
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}
