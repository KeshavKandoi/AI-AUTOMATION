import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Check, X } from 'lucide-react'
import { tasksApi } from '@/api/tasks'
import { useAuthStore } from '@/store/authStore'
import Badge from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import type { Task } from '@/types/tasks'

type PriorityFilter = 'all' | 'high' | 'medium' | 'low'
type StatusFilter = 'all' | 'open' | 'approved' | 'rejected' | 'issue_created' | 'email_sent' | 'event_created'

const priorityTone: Record<string, 'alert' | 'amber' | 'neutral'> = {
  high: 'alert',
  medium: 'amber',
  low: 'neutral',
}

export default function Tasks() {
  const orgId = useAuthStore((s) => s.user?.organization_id)
  const queryClient = useQueryClient()

  const [search, setSearch] = useState('')
  const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')

  const { data: tasks, isLoading } = useQuery({
    queryKey: ['tasks', orgId],
    queryFn: () => tasksApi.list(orgId!).then((r) => r.data),
    enabled: !!orgId,
  })

  const approveMutation = useMutation({
    mutationFn: (taskId: string) => tasksApi.approve(taskId),
    onMutate: async (taskId) => {
      await queryClient.cancelQueries({ queryKey: ['tasks', orgId] })
      const prev = queryClient.getQueryData<Task[]>(['tasks', orgId])
      queryClient.setQueryData<Task[]>(['tasks', orgId], (old) =>
        old?.map((t) => (t.id === taskId ? { ...t, status: 'approved' } : t))
      )
      return { prev }
    },
    onError: (_err, _taskId, context) => {
      if (context?.prev) queryClient.setQueryData(['tasks', orgId], context.prev)
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['tasks', orgId] }),
  })

  const rejectMutation = useMutation({
    mutationFn: (taskId: string) => tasksApi.reject(taskId),
    onMutate: async (taskId) => {
      await queryClient.cancelQueries({ queryKey: ['tasks', orgId] })
      const prev = queryClient.getQueryData<Task[]>(['tasks', orgId])
      queryClient.setQueryData<Task[]>(['tasks', orgId], (old) =>
        old?.map((t) => (t.id === taskId ? { ...t, status: 'rejected' } : t))
      )
      return { prev }
    },
    onError: (_err, _taskId, context) => {
      if (context?.prev) queryClient.setQueryData(['tasks', orgId], context.prev)
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['tasks', orgId] }),
  })

  const filtered = useMemo(() => {
    if (!tasks) return []
    return tasks.filter((t) => {
      if (priorityFilter !== 'all' && t.priority !== priorityFilter) return false
      if (statusFilter !== 'all' && t.status !== statusFilter) return false
      if (search && !t.title.toLowerCase().includes(search.toLowerCase())) return false
      return true
    })
  }, [tasks, priorityFilter, statusFilter, search])

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto">
      <div className="mb-6 flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
            Tasks
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            {filtered.length} of {tasks?.length ?? 0} tasks
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-5">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-faint)]" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tasks..."
            className="w-56 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] pl-8 pr-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-faint)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)]"
          />
        </div>

        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value as PriorityFilter)}
          className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-signal)]"
        >
          <option value="all">All priorities</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
          className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-signal)]"
        >
          <option value="all">All statuses</option>
          <option value="open">Open</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="issue_created">Issue created</option>
          <option value="email_sent">Email sent</option>
          <option value="event_created">Event created</option>
        </select>
      </div>

      <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60 backdrop-blur-xl overflow-hidden">
        {isLoading ? (
          <div className="p-5 space-y-2">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-12 rounded-lg bg-[var(--color-surface-hover)] animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-10 text-center">
            <p className="text-sm text-[var(--color-text-faint)]">No tasks match your filters.</p>
          </div>
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            <AnimatePresence initial={false}>
              {filtered.map((task) => (
                <motion.div
                  key={task.id}
                  layout
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center justify-between gap-4 px-5 py-3.5"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-[var(--color-text-primary)] truncate">{task.title}</p>
                    <p className="text-xs text-[var(--color-text-faint)] truncate mt-0.5">
                      {task.description}
                    </p>
                    <p className="text-[11px] text-[var(--color-text-faint)] font-mono mt-1">
                      {task.source}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Badge tone={priorityTone[task.priority] ?? 'neutral'}>{task.priority}</Badge>
                    <Badge tone={task.status === 'open' ? 'neutral' : 'signal'}>{task.status}</Badge>

                    {task.status === 'open' && (
                      <div className="flex items-center gap-1 ml-1">
                        <Button
                          variant="secondary"
                          className="!p-2"
                          onClick={() => approveMutation.mutate(task.id)}
                          loading={approveMutation.isPending && approveMutation.variables === task.id}
                        >
                          <Check size={14} className="text-[var(--color-signal)]" />
                        </Button>
                        <Button
                          variant="secondary"
                          className="!p-2"
                          onClick={() => rejectMutation.mutate(task.id)}
                          loading={rejectMutation.isPending && rejectMutation.variables === task.id}
                        >
                          <X size={14} className="text-[var(--color-alert)]" />
                        </Button>
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  )
}
