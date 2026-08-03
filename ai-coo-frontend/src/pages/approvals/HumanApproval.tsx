import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Check, X, GitBranch, Mail, Calendar as CalendarIcon, ExternalLink } from 'lucide-react'
import { tasksApi } from '@/api/tasks'
import { useAuthStore } from '@/store/authStore'
import Badge from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'

const priorityTone: Record<string, 'alert' | 'amber' | 'neutral'> = {
  high: 'alert',
  medium: 'amber',
  low: 'neutral',
}

function providerFromSourceRef(sourceRef?: string | null): 'github' | 'gmail' | 'calendar' | null {
  if (!sourceRef) return null
  if (sourceRef.startsWith('github:')) return 'github'
  if (sourceRef.startsWith('gmail:')) return 'gmail'
  if (sourceRef.startsWith('calendar:')) return 'calendar'
  return null
}

function defaultTimeRange() {
  const start = new Date(Date.now() + 60 * 60 * 1000)
  const end = new Date(start.getTime() + 30 * 60 * 1000)
  const toLocalInput = (d: Date) => {
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
  }
  return { start: toLocalInput(start), end: toLocalInput(end) }
}

export default function HumanApproval() {
  const orgId = useAuthStore((s) => s.user?.organization_id)
  const queryClient = useQueryClient()
  const [calendarTimes, setCalendarTimes] = useState<Record<string, { start: string; end: string }>>({})

  const { data: tasks, isLoading } = useQuery({
    queryKey: ['tasks', orgId],
    queryFn: () => tasksApi.list(orgId!).then((r) => r.data),
    enabled: !!orgId,
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['tasks', orgId] })

  const approveMutation = useMutation({
    mutationFn: (taskId: string) => tasksApi.approve(taskId),
    onSettled: invalidate,
  })
  const rejectMutation = useMutation({
    mutationFn: (taskId: string) => tasksApi.reject(taskId),
    onSettled: invalidate,
  })
  const resolveGithubMutation = useMutation({
    mutationFn: (taskId: string) => tasksApi.resolveGithub(taskId),
    onSettled: invalidate,
  })
  const resolveGmailMutation = useMutation({
    mutationFn: (taskId: string) => tasksApi.resolveGmail(taskId),
    onSettled: invalidate,
  })
  const resolveCalendarMutation = useMutation({
    mutationFn: ({ taskId, start, end }: { taskId: string; start: string; end: string }) =>
      tasksApi.resolveCalendar(taskId, new Date(start).toISOString(), new Date(end).toISOString()),
    onSettled: invalidate,
  })

  const awaitingApproval = useMemo(() => tasks?.filter((t) => t.status === 'open') ?? [], [tasks])
  const awaitingResolution = useMemo(() => tasks?.filter((t) => t.status === 'approved') ?? [], [tasks])

  const getCalendarTimes = (taskId: string) => calendarTimes[taskId] ?? defaultTimeRange()

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
          Human Approval
        </h1>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          Review AI-proposed tasks before they take real action
        </p>
      </div>

      <section className="mb-8">
        <h2 className="text-sm font-medium text-[var(--color-text-primary)] mb-3">
          Awaiting approval
          <span className="ml-2 text-[var(--color-text-faint)]">({awaitingApproval.length})</span>
        </h2>

        <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60 backdrop-blur-xl overflow-hidden">
          {isLoading ? (
            <div className="p-5 space-y-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-14 rounded-lg bg-[var(--color-surface-hover)] animate-pulse" />
              ))}
            </div>
          ) : awaitingApproval.length === 0 ? (
            <p className="p-6 text-sm text-[var(--color-text-faint)]">Nothing awaiting approval.</p>
          ) : (
            <div className="divide-y divide-[var(--color-border)]">
              <AnimatePresence initial={false}>
                {awaitingApproval.map((task) => (
                  <motion.div
                    key={task.id}
                    layout
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="flex items-center justify-between gap-4 px-5 py-4"
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
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>
      </section>

      <section>
        <h2 className="text-sm font-medium text-[var(--color-text-primary)] mb-3">
          Awaiting resolution
          <span className="ml-2 text-[var(--color-text-faint)]">({awaitingResolution.length})</span>
        </h2>

        <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60 backdrop-blur-xl overflow-hidden">
          {isLoading ? (
            <div className="p-5 space-y-2">
              {[...Array(2)].map((_, i) => (
                <div key={i} className="h-14 rounded-lg bg-[var(--color-surface-hover)] animate-pulse" />
              ))}
            </div>
          ) : awaitingResolution.length === 0 ? (
            <p className="p-6 text-sm text-[var(--color-text-faint)]">Nothing awaiting resolution.</p>
          ) : (
            <div className="divide-y divide-[var(--color-border)]">
              <AnimatePresence initial={false}>
                {awaitingResolution.map((task) => {
                  const provider = providerFromSourceRef(task.source_ref)
                  const times = getCalendarTimes(task.id)

                  return (
                    <motion.div
                      key={task.id}
                      layout
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="flex items-center justify-between gap-4 px-5 py-4"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-[var(--color-text-primary)] truncate">{task.title}</p>
                        <p className="text-xs text-[var(--color-text-faint)] truncate mt-0.5">
                          {task.description}
                        </p>
                        {task.source_ref && (
                          <p className="text-[11px] text-[var(--color-text-faint)] font-mono mt-1 truncate">
                            {task.source_ref}
                          </p>
                        )}
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <Badge tone={priorityTone[task.priority] ?? 'neutral'}>{task.priority}</Badge>

                        {provider === 'github' && (
                          <Button
                            variant="secondary"
                            onClick={() => resolveGithubMutation.mutate(task.id)}
                            loading={
                              resolveGithubMutation.isPending &&
                              resolveGithubMutation.variables === task.id
                            }
                          >
                            <GitBranch size={14} />
                            Resolve on GitHub
                          </Button>
                        )}

                        {provider === 'gmail' && (
                          <Button
                            variant="secondary"
                            onClick={() => resolveGmailMutation.mutate(task.id)}
                            loading={
                              resolveGmailMutation.isPending &&
                              resolveGmailMutation.variables === task.id
                            }
                          >
                            <Mail size={14} />
                            Send email
                          </Button>
                        )}

                        {provider === 'calendar' && (
                          <div className="flex items-center gap-2">
                            <input
                              type="datetime-local"
                              value={times.start}
                              onChange={(e) =>
                                setCalendarTimes((prev) => ({
                                  ...prev,
                                  [task.id]: { ...times, start: e.target.value },
                                }))
                              }
                              className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 text-xs text-[var(--color-text-primary)]"
                            />
                            <Button
                              variant="secondary"
                              onClick={() =>
                                resolveCalendarMutation.mutate({
                                  taskId: task.id,
                                  start: times.start,
                                  end: times.end,
                                })
                              }
                              loading={
                                resolveCalendarMutation.isPending &&
                                resolveCalendarMutation.variables?.taskId === task.id
                              }
                            >
                              <CalendarIcon size={14} />
                              Create event
                            </Button>
                          </div>
                        )}

                        {!provider && (
                          <span className="text-xs text-[var(--color-text-faint)] flex items-center gap-1">
                            No linked source
                            <ExternalLink size={12} />
                          </span>
                        )}
                      </div>
                    </motion.div>
                  )
                })}
              </AnimatePresence>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
