import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import { Search, Check, X, Trash2, ListTodo, Sparkles, RotateCw } from 'lucide-react'
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
  const reduceMotion = useReducedMotion()

  const [search, setSearch] = useState('')
  const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')

  const { data: tasks, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['tasks', orgId],
    queryFn: () => tasksApi.list(orgId!).then((r) => r.data),
    enabled: !!orgId,
    staleTime: 90_000,
  })

  const deleteMutation = useMutation({
    mutationFn: (taskId: string) => tasksApi.delete(taskId),
    onMutate: async (taskId) => {
      await queryClient.cancelQueries({ queryKey: ['tasks', orgId] })
      const previous = queryClient.getQueryData<Task[]>(['tasks', orgId])
      queryClient.setQueryData<Task[]>(['tasks', orgId], (current) => current?.filter((task) => task.id !== taskId))
      return { previous }
    },
    onError: (_error, _taskId, context) => {
      if (context?.previous) queryClient.setQueryData(['tasks', orgId], context.previous)
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['tasks', orgId] }),
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
      const term = search.toLowerCase()
      if (search && ![t.title, t.description, t.source].some((value) => value?.toLowerCase().includes(term))) return false
      return true
    })
  }, [tasks, priorityFilter, statusFilter, search])

  return (
    <div className="relative isolate mx-auto max-w-7xl overflow-hidden p-5 md:p-8">
      <div aria-hidden="true" className="pointer-events-none absolute -right-28 -top-36 -z-10 h-96 w-96 rounded-full bg-[var(--color-signal)]/[0.06] blur-3xl" />
      <motion.header
        initial={reduceMotion ? false : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: reduceMotion ? 0 : 0.35, ease: 'easeOut' }}
        className="mb-6 flex items-end justify-between flex-wrap gap-3"
      >
        <div>
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-[var(--color-signal)]/20 bg-[var(--color-signal-dim)] px-3 py-1 text-[11px] font-medium tracking-wide text-[var(--color-signal)]">
            <Sparkles size={13} /> WORKSPACE ACTIONS
          </div>
          <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight text-[var(--color-text-primary)]">
            Tasks
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            {filtered.length} of {tasks?.length ?? 0} tasks · review and manage work created from your connected tools
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-[var(--color-text-faint)]">
          {isFetching && <RotateCw size={13} className="animate-spin motion-reduce:animate-none" />}
          {isFetching ? 'Updating tasks' : 'Tasks stay in sync'}
        </div>
      </motion.header>

      <div className="mb-5 flex items-start gap-3 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/55 px-4 py-3.5 text-sm text-[var(--color-text-muted)] backdrop-blur-xl">
        <ListTodo size={17} className="mt-0.5 shrink-0 text-[var(--color-signal)]" />
        <p><span className="font-medium text-[var(--color-text-primary)]">What are these?</span> WorkForge tasks are action items created from events in connected services, such as GitHub issues or workflow runs. Approve or reject open items to handle them; delete removes only the task from WorkForge.</p>
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

      <div className="overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/65 shadow-[0_18px_55px_-38px_rgba(0,0,0,0.8)] backdrop-blur-xl">
        {isLoading ? (
          <div className="p-5 space-y-2">
            {[...Array(6)].map((_, i) => (
              <motion.div key={i} initial={reduceMotion ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: reduceMotion ? 0 : i * 0.045 }} className="h-[76px] rounded-xl bg-[var(--color-surface-hover)] animate-pulse motion-reduce:animate-none" />
            ))}
          </div>
        ) : isError && !tasks ? (
          <div className="p-10 text-center">
            <p className="text-sm text-[var(--color-text-primary)]">Tasks could not be loaded.</p>
            <p className="mt-1 text-xs text-[var(--color-text-faint)]">Check your connection and try again.</p>
            <Button variant="secondary" className="mt-4" onClick={() => void refetch()}>Try again</Button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-10 text-center">
            <p className="text-sm text-[var(--color-text-faint)]">{tasks?.length ? 'No tasks match your filters.' : 'No tasks yet. WorkForge will show action items here when connected services or workflows create them.'}</p>
          </div>
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            <AnimatePresence initial={false}>
              {filtered.map((task) => (
                <motion.div
                  key={task.id}
                  layout={!reduceMotion}
                  initial={reduceMotion ? false : { opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: reduceMotion ? 0 : 0.22, ease: 'easeOut' }}
                  className="group flex flex-col items-start justify-between gap-3 px-4 py-4 transition-colors hover:bg-[var(--color-surface-hover)]/45 sm:flex-row sm:items-center sm:gap-4 sm:px-5"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-[var(--color-text-primary)] truncate">{task.title}</p>
                    <p className="text-xs text-[var(--color-text-faint)] truncate mt-0.5">
                      {task.description}
                    </p>
                    <p className="mt-2 inline-flex rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-0.5 text-[10px] text-[var(--color-text-faint)] font-mono">
                      {task.source.replaceAll('_', ' ')}
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    <Badge tone={priorityTone[task.priority] ?? 'neutral'}>{task.priority}</Badge>
                    <Badge tone={task.status === 'open' ? 'neutral' : 'signal'}>{task.status}</Badge>

                    {task.status === 'open' && (
                      <div className="flex items-center gap-1 ml-1">
                        <Button
                          variant="secondary"
                          className="!p-2"
                          aria-label={`Approve task: ${task.title}`}
                          title="Approve task"
                          onClick={() => approveMutation.mutate(task.id)}
                          loading={approveMutation.isPending && approveMutation.variables === task.id}
                        >
                          <Check size={14} className="text-[var(--color-signal)]" />
                        </Button>
                        <Button
                          variant="secondary"
                          className="!p-2"
                          aria-label={`Reject task: ${task.title}`}
                          title="Reject task"
                          onClick={() => rejectMutation.mutate(task.id)}
                          loading={rejectMutation.isPending && rejectMutation.variables === task.id}
                        >
                          <X size={14} className="text-[var(--color-alert)]" />
                        </Button>
                      </div>
                    )}
                    <Button
                      variant="secondary"
                      className="!p-2 text-[var(--color-text-faint)] hover:!border-[var(--color-alert)]/50 hover:!text-[var(--color-alert)]"
                      aria-label={`Delete task: ${task.title}`}
                      title="Delete task"
                      loading={deleteMutation.isPending && deleteMutation.variables === task.id}
                      onClick={() => {
                        if (window.confirm(`Delete “${task.title}” from WorkForge? This does not delete anything in the connected service.`)) {
                          deleteMutation.reset()
                          deleteMutation.mutate(task.id)
                        }
                      }}
                    >
                      <Trash2 size={14} />
                    </Button>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
      {deleteMutation.isError && (
        <p role="alert" className="mt-3 text-sm text-[var(--color-alert)]">Could not delete that task. It has been restored in the list; please try again.</p>
      )}
    </div>
  )
}
