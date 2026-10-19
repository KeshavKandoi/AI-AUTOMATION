import { useQuery } from '@tanstack/react-query'
import { motion, useReducedMotion } from 'framer-motion'
import { ListTodo, AlertCircle, Workflow, Activity, Plug } from 'lucide-react'
import { tasksApi } from '@/api/tasks'
import { schedulerApi } from '@/api/scheduler'
import { integrationsApi } from '@/api/integrations'
import { organizationSettingsService } from '@/services/organization-settings'
import { auditLogsService, type AuditLogEntry } from '@/services/audit-logs'
import { getModuleIcon, formatActionLabel } from '@/lib/auditLogDisplay'
import { memoryService, type MemoryEntry } from '@/services/memory'
import { getCategoryIcon } from '@/lib/memoryDisplay'
import { Brain, Pin, Star } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import StatCard from '@/components/ui/StatCard'

import { formatDistanceToNow } from 'date-fns'

const PROVIDER_LABELS: Record<string, string> = {
  github: 'GitHub',
  gmail: 'Gmail',
}

export default function Dashboard() {
  const orgId = useAuthStore((s) => s.user?.organization_id)
  const reduceMotion = useReducedMotion()

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
  const discordStatus = useQuery({
    queryKey: ['organization-settings', 'discord-webhook', orgId],
    queryFn: organizationSettingsService.getDiscordWebhook,
    enabled: !!orgId,
  })

  const { data: activityData, isLoading: activityLoading } = useQuery({
    queryKey: ['audit-logs', 'dashboard', orgId],
    queryFn: () => auditLogsService.list(orgId!, 8, 0),
    enabled: !!orgId,
  })
  const activity = activityData?.items

  const { data: recentMemories, isLoading: memoriesLoading } = useQuery({
    queryKey: ['memory', 'recent', orgId],
    queryFn: () => memoryService.getRecent(orgId!, 5),
    enabled: !!orgId,
  })

  const highPriority = tasks?.filter((t) => t.priority === 'high').length ?? 0
  const openTasks = tasks?.filter((t) => t.status === 'open').length ?? 0
  const activeJobs = scheduler?.jobs.length ?? 0
  const connectedCount = (integrations?.filter((i) => i.provider !== 'discord' && i.connected).length ?? 0) + (discordStatus.data?.configured ? 1 : 0)

  const panelClass = 'rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/70 backdrop-blur-xl shadow-[0_18px_55px_-38px_rgba(0,0,0,0.8)]'
  const sectionHeadingClass = 'text-sm font-semibold tracking-wide text-[var(--color-text-primary)]'
  const rowMotion = {
    initial: reduceMotion ? false : { opacity: 0, y: 8 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: reduceMotion ? 0 : 0.28, ease: 'easeOut' as const },
  }

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-5 p-5 md:gap-6 md:p-8">
      <header className="flex flex-col gap-1">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
            Dashboard
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Your workspace at a glance
          </p>
        </div>
      </header>

      <motion.div
        initial="hidden"
        animate="show"
        variants={{ hidden: {}, show: { transition: { staggerChildren: reduceMotion ? 0 : 0.07 } } }}
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <StatCard label="Open tasks" value={openTasks} icon={ListTodo} tone="signal" loading={tasksLoading} />
        <StatCard label="High priority" value={highPriority} icon={AlertCircle} tone="alert" loading={tasksLoading} />
        <StatCard label="Scheduled jobs" value={activeJobs} icon={Workflow} tone="amber" loading={schedulerLoading} />
        <StatCard label="Connected integrations" value={connectedCount} icon={Plug} tone="signal" loading={integrationsLoading || discordStatus.isLoading} />
      </motion.div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className={`${panelClass} lg:col-span-2 p-5 md:p-6`}>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className={sectionHeadingClass}>Recent tasks</h2>
              <p className="mt-1 text-xs text-[var(--color-text-faint)]">The latest work across your workspace</p>
            </div>
            <ListTodo size={16} className="text-[var(--color-signal)]" />
          </div>
          {tasksLoading ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-10 rounded-lg bg-[var(--color-surface-hover)] animate-pulse" />
              ))}
            </div>
          ) : tasks && tasks.length > 0 ? (
            <div className="flex flex-col divide-y divide-[var(--color-border)]">
              {tasks.slice(0, 6).map((task) => (
                <motion.div key={task.id} {...rowMotion} whileHover={reduceMotion ? undefined : { x: 3 }} className="group -mx-2 flex items-center justify-between gap-3 rounded-xl px-2 py-3 transition-colors hover:bg-[var(--color-surface-hover)]/70">
                  <div className="min-w-0">
                    <p className="text-sm text-[var(--color-text-primary)] truncate">{task.title}</p>
                    <p className="mt-0.5 text-xs text-[var(--color-text-faint)] font-mono">{task.source}</p>
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
                </motion.div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--color-text-faint)]">No tasks yet.</p>
          )}
        </div>

        <div className={`${panelClass} p-5 md:p-6`}>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className={sectionHeadingClass}>Integrations</h2>
              <p className="mt-1 text-xs text-[var(--color-text-faint)]">Your connected services</p>
            </div>
            <Plug size={16} className="text-[var(--color-signal)]" />
          </div>
          {integrationsLoading || discordStatus.isLoading ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-9 rounded-lg bg-[var(--color-surface-hover)] animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {(integrations ?? []).filter((i) => i.provider !== 'discord').map((i) => (
                <motion.div key={i.id} {...rowMotion} className="flex items-center justify-between rounded-xl px-2 py-3 hover:bg-[var(--color-surface-hover)]/70">
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
                </motion.div>
              ))}
              <div className="flex items-center justify-between rounded-xl px-2 py-3 hover:bg-[var(--color-surface-hover)]/70">
                <span className="text-sm text-[var(--color-text-primary)]">Discord</span>
                <span className={discordStatus.isError ? 'text-xs text-[var(--color-alert)]' : discordStatus.data?.configured ? 'text-xs text-[var(--color-signal)]' : 'text-xs text-[var(--color-text-faint)]'}>
                  {discordStatus.isError ? 'Status unavailable' : discordStatus.data?.configured ? 'Connected' : 'Not connected'}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className={`${panelClass} p-5 md:p-6`}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className={sectionHeadingClass}>Recent memories</h2>
            <p className="mt-1 text-xs text-[var(--color-text-faint)]">Useful context saved for your workspace</p>
          </div>
          <Brain size={16} className="text-[var(--color-signal)]" />
        </div>
        {memoriesLoading ? (
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-9 rounded-lg bg-[var(--color-surface-hover)] animate-pulse" />
            ))}
          </div>
        ) : recentMemories && recentMemories.length > 0 ? (
          <div className="flex flex-col divide-y divide-[var(--color-border)]">
            {recentMemories.map((m: MemoryEntry) => {
              const Icon = getCategoryIcon(m.category)
              return (
                <motion.div key={m.id} {...rowMotion} className="py-3 flex items-center gap-3">
                  <Icon size={13} className="shrink-0 text-[var(--color-text-faint)]" />
                  <span className="text-sm text-[var(--color-text-muted)] truncate flex-1 min-w-0">
                    {m.title ?? 'Untitled'}
                  </span>
                  {m.pinned && <Pin size={11} className="text-[var(--color-signal)] shrink-0" fill="currentColor" />}
                  {m.favorited && <Star size={11} className="text-[var(--color-amber)] shrink-0" fill="currentColor" />}
                </motion.div>
              )
            })}
          </div>
        ) : (
          <p className="text-sm text-[var(--color-text-faint)]">No memories yet.</p>
        )}
      </div>

      <div className={`${panelClass} p-5 md:p-6`}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className={sectionHeadingClass}>Recent activity</h2>
            <p className="mt-1 text-xs text-[var(--color-text-faint)]">A timeline of what has happened</p>
          </div>
          <Activity size={16} className="text-[var(--color-signal)]" />
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
                  initial={reduceMotion ? false : { opacity: 0, y: 7 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: reduceMotion ? 0 : 0.25, delay: reduceMotion ? 0 : idx * 0.035 }}
                  className="flex items-center justify-between gap-3 rounded-xl px-2 py-3 hover:bg-[var(--color-surface-hover)]/70"
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
