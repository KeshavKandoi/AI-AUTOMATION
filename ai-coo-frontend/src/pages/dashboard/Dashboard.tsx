import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { ListTodo, AlertCircle, Workflow, Activity, Plug } from 'lucide-react'
import { tasksApi } from '@/api/tasks'
import { schedulerApi } from '@/api/scheduler'
import { integrationsApi } from '@/api/integrations'
import { auditLogsService, type AuditLogEntry } from '@/services/audit-logs'
import { getModuleIcon, formatActionLabel } from '@/lib/auditLogDisplay'
import { useAuthStore } from '@/store/authStore'
import StatCard from '@/components/ui/StatCard'

import { formatDistanceToNow } from 'date-fns'

const PROVIDER_LABELS: Record<string, string> = {
  github: 'GitHub',
  gmail: 'Gmail',
  calendar: 'Google Calendar',
  discord: 'Discord',
}

export default function Dashboard() {
  const orgId = useAuthStore((s) => s.user?.organization_id)

  const { data: tasks, isLoading: tasksLoading } = useQuery({
    queryKey: ['tasks', orgId],
    queryFn: () => tasksApi.list(orgId!).then((r) => r.data),
    enabled: !!orgId,
  })

  const { data: scheduler, isLoading: schedulerLoading } = useQuery({
    queryKey: ['scheduler-status'],
    queryFn: () => schedulerApi.status().then((r) => r.data),
  })

  const { data: integrations, isLoading: integrationsLoading } = useQuery({
    queryKey: ['integrations', orgId],
    queryFn: () => integrationsApi.list(orgId!).then((r) => r.data),
    enabled: !!orgId,
  })

  const { data: activityData, isLoading: activityLoading } = useQuery({
    queryKey: ['audit-logs', 'dashboard', orgId],
    queryFn: () => auditLogsService.list(orgId!, 8, 0),
    enabled: !!orgId,
  })
  const activity = activityData?.items

  const highPriority = tasks?.filter((t) => t.priority === 'high').length ?? 0
  const openTasks = tasks?.filter((t) => t.status === 'open').length ?? 0
  const activeJobs = scheduler?.jobs.length ?? 0
  const connectedCount = integrations?.filter((i) => i.connected).length ?? 0

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
          Dashboard
        </h1>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          Live status across your AI COO
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard label="Open tasks" value={openTasks} icon={ListTodo} tone="signal" loading={tasksLoading} />
        <StatCard label="High priority" value={highPriority} icon={AlertCircle} tone="alert" loading={tasksLoading} />
        <StatCard label="Scheduled jobs" value={activeJobs} icon={Workflow} tone="amber" loading={schedulerLoading} />
        <StatCard label="Connected integrations" value={connectedCount} icon={Plug} tone="signal" loading={integrationsLoading} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="lg:col-span-2 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60 backdrop-blur-xl p-5">
          <h2 className="text-sm font-medium text-[var(--color-text-primary)] mb-4">Recent tasks</h2>
          {tasksLoading ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-10 rounded-lg bg-[var(--color-surface-hover)] animate-pulse" />
              ))}
            </div>
          ) : tasks && tasks.length > 0 ? (
            <div className="flex flex-col divide-y divide-[var(--color-border)]">
              {tasks.slice(0, 6).map((task) => (
                <div key={task.id} className="py-2.5 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm text-[var(--color-text-primary)] truncate">{task.title}</p>
                    <p className="text-xs text-[var(--color-text-faint)] font-mono">{task.source}</p>
                  </div>
                  <span
                    className={
                      task.priority === 'high'
                        ? 'text-[10px] uppercase tracking-wide text-[var(--color-alert)] bg-[var(--color-alert-dim)] rounded px-2 py-1 shrink-0'
                        : task.priority === 'medium'
                        ? 'text-[10px] uppercase tracking-wide text-[var(--color-amber)] bg-[var(--color-amber-dim)] rounded px-2 py-1 shrink-0'
                        : 'text-[10px] uppercase tracking-wide text-[var(--color-text-muted)] bg-[var(--color-surface-hover)] rounded px-2 py-1 shrink-0'
                    }
                  >
                    {task.priority}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--color-text-faint)]">No tasks yet.</p>
          )}
        </div>

        <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60 backdrop-blur-xl p-5">
          <h2 className="text-sm font-medium text-[var(--color-text-primary)] mb-4">Integrations</h2>
          {integrationsLoading ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-9 rounded-lg bg-[var(--color-surface-hover)] animate-pulse" />
              ))}
            </div>
          ) : integrations && integrations.length > 0 ? (
            <div className="flex flex-col gap-2">
              {integrations.map((i) => (
                <div key={i.id} className="flex items-center justify-between py-1.5">
                  <span className="text-sm text-[var(--color-text-primary)]">
                    {PROVIDER_LABELS[i.provider] ?? i.provider}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span
                      className={
                        i.connected
                          ? 'h-1.5 w-1.5 rounded-full bg-[var(--color-signal)] animate-pulse-signal'
                          : 'h-1.5 w-1.5 rounded-full bg-[var(--color-text-faint)]'
                      }
                    />
                    <span
                      className={
                        i.connected
                          ? 'text-xs text-[var(--color-signal)]'
                          : 'text-xs text-[var(--color-text-faint)]'
                      }
                    >
                      {i.connected ? 'Connected' : 'Disconnected'}
                    </span>
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--color-text-faint)]">No integrations connected.</p>
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60 backdrop-blur-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-[var(--color-text-primary)]">Recent activity</h2>
          <Activity size={14} className="text-[var(--color-text-faint)]" />
        </div>
        {activityLoading ? (
          <div className="space-y-2">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-8 rounded-lg bg-[var(--color-surface-hover)] animate-pulse" />
            ))}
          </div>
        ) : activity && activity.length > 0 ? (
          <div className="flex flex-col divide-y divide-[var(--color-border)]">
            {activity.map((log: AuditLogEntry, idx: number) => {
              const Icon = getModuleIcon(log.module)
              return (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: idx * 0.03 }}
                  className="py-2.5 flex items-center justify-between gap-3"
                >
                  <span className="flex items-center gap-2 text-sm text-[var(--color-text-muted)] min-w-0">
                    <Icon size={13} className="shrink-0 text-[var(--color-text-faint)]" />
                    <span className="truncate">{log.summary ?? formatActionLabel(log.action)}</span>
                  </span>
                  <span className="text-xs text-[var(--color-text-faint)] font-mono shrink-0">
                    {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                  </span>
                </motion.div>
              )
            })}
          </div>
        ) : (
          <p className="text-sm text-[var(--color-text-faint)]">No activity yet.</p>
        )}
      </div>
    </div>
  )
}
