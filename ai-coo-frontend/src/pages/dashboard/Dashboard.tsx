import { useQuery } from '@tanstack/react-query'
import { ListTodo, AlertCircle, Workflow, Activity } from 'lucide-react'
import { tasksApi } from '@/api/tasks'
import { schedulerApi } from '@/api/scheduler'
import { useAuthStore } from '@/store/authStore'
import StatCard from '@/components/ui/StatCard'

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

  const highPriority = tasks?.filter((t) => t.priority === 'high').length ?? 0
  const openTasks = tasks?.filter((t) => t.status === 'open').length ?? 0
  const activeJobs = scheduler?.jobs.length ?? 0

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

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Open tasks" value={openTasks} icon={ListTodo} tone="signal" loading={tasksLoading} />
        <StatCard label="High priority" value={highPriority} icon={AlertCircle} tone="alert" loading={tasksLoading} />
        <StatCard label="Scheduled jobs" value={activeJobs} icon={Workflow} tone="amber" loading={schedulerLoading} />
        <StatCard
          label="Scheduler"
          value={scheduler?.running ? 'Running' : '—'}
          icon={Activity}
          tone={scheduler?.running ? 'signal' : 'neutral'}
          loading={schedulerLoading}
        />
      </div>

      <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60 backdrop-blur-xl p-5">
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
    </div>
  )
}
