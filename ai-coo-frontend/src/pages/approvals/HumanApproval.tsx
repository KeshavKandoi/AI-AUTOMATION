import { useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import { ArrowRight, Check, ClipboardCheck, GitBranch, Mail, ShieldCheck, Workflow, X, ExternalLink } from 'lucide-react'
import { Link } from 'react-router-dom'
import { tasksApi } from '@/api/tasks'
import { useAuthStore } from '@/store/authStore'
import Badge from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'

const priorityTone: Record<string, 'alert' | 'amber' | 'neutral'> = {
  high: 'alert',
  medium: 'amber',
  low: 'neutral',
}

function providerFromSourceRef(sourceRef?: string | null): 'github' | 'gmail' | null {
  if (!sourceRef) return null
  if (sourceRef.startsWith('github:')) return 'github'
  if (sourceRef.startsWith('gmail:')) return 'gmail'
  return null
}

export default function HumanApproval() {
  const reduceMotion = useReducedMotion()
  const orgId = useAuthStore((s) => s.user?.organization_id)
  const queryClient = useQueryClient()

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
  const awaitingApproval = useMemo(() => tasks?.filter((t) => t.status === 'open') ?? [], [tasks])
  const awaitingResolution = useMemo(() => tasks?.filter((t) => t.status === 'approved') ?? [], [tasks])


  return (
    <div className="relative isolate mx-auto max-w-7xl overflow-hidden p-5 md:p-8">
      <div aria-hidden="true" className="pointer-events-none absolute -right-24 -top-32 -z-10 h-96 w-96 rounded-full bg-[var(--color-signal)]/[0.06] blur-3xl" />
      <motion.header
        initial={reduceMotion ? false : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: reduceMotion ? 0 : 0.35 }}
        className="mb-6 flex flex-wrap items-center justify-between gap-4"
      >
        <div className="flex items-center gap-4">
          <span className="grid h-12 w-12 place-items-center rounded-2xl border border-[var(--color-signal)]/20 bg-[var(--color-signal-dim)] text-[var(--color-signal)]"><ShieldCheck size={22} /></span>
          <div>
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--color-signal)]">Review before action</p>
            <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">Human Approval</h1>
            <p className="mt-1 text-sm text-[var(--color-text-muted)]">Keep a person in control before automations act.</p>
          </div>
        </div>
        <Link to="/workflows" className="inline-flex items-center gap-2 rounded-xl border border-[var(--color-signal)]/25 bg-[var(--color-signal-dim)] px-4 py-2.5 text-sm font-medium text-[var(--color-signal)] transition-colors hover:border-[var(--color-signal)]/50 hover:bg-[var(--color-signal)]/15">
          <Workflow size={15} /> Create an approval workflow <ArrowRight size={14} />
        </Link>
      </motion.header>

      <motion.aside
        initial={reduceMotion ? false : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: reduceMotion ? 0 : 0.3, delay: reduceMotion ? 0 : 0.04 }}
        className="mb-7 grid gap-4 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/70 p-4 backdrop-blur-xl md:grid-cols-[1fr_auto] md:items-center md:p-5"
      >
        <div className="flex items-start gap-3">
          <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[var(--color-signal-dim)] text-[var(--color-signal)]"><ClipboardCheck size={17} /></span>
          <div>
            <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">What is this queue for?</h2>
            <p className="mt-1 max-w-3xl text-xs leading-relaxed text-[var(--color-text-muted)]">WorkForge puts tasks proposed by its automations here for review. Approve or reject each task; approved GitHub and Gmail tasks can then be completed with the follow-up actions shown on the task.</p>
            <p className="mt-2 text-xs leading-relaxed text-[var(--color-text-faint)]"><span className="font-medium text-[var(--color-text-primary)]">To create approval items:</span> open Workflow Automations, create a workflow for an event, and add the <span className="text-[var(--color-signal)]">Create task</span> action. New tasks appear in Awaiting approval.</p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 md:min-w-48 md:grid-cols-1">
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-void)]/40 px-3 py-2">
            <p className="text-[10px] uppercase tracking-wide text-[var(--color-text-faint)]">Awaiting review</p>
            <p className="mt-0.5 text-lg font-semibold tabular-nums text-[var(--color-text-primary)]">{awaitingApproval.length}</p>
          </div>
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-void)]/40 px-3 py-2">
            <p className="text-[10px] uppercase tracking-wide text-[var(--color-text-faint)]">Ready for follow-up</p>
            <p className="mt-0.5 text-lg font-semibold tabular-nums text-[var(--color-signal)]">{awaitingResolution.length}</p>
          </div>
        </div>
      </motion.aside>

      <motion.section initial={reduceMotion ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduceMotion ? 0 : 0.3, delay: reduceMotion ? 0 : 0.08 }} className="mb-8">
        <h2 className="text-sm font-medium text-[var(--color-text-primary)] mb-3">
          Awaiting approval
          <span className="ml-2 text-[var(--color-text-faint)]">({awaitingApproval.length})</span>
        </h2>

        <div className="overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/75 shadow-lg shadow-black/5 backdrop-blur-xl">
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
                    initial={reduceMotion ? false : { opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={reduceMotion ? undefined : { opacity: 0, y: -6 }}
                    transition={{ duration: reduceMotion ? 0 : 0.2 }}
                    className="flex flex-col justify-between gap-3 px-4 py-4 transition-colors hover:bg-[var(--color-surface-hover)]/50 sm:flex-row sm:items-center sm:gap-4 sm:px-5"
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
                        className="!px-3 !py-2"
                        aria-label={`Approve ${task.title}`}
                        title="Approve task"
                        onClick={() => approveMutation.mutate(task.id)}
                        loading={approveMutation.isPending && approveMutation.variables === task.id}
                      >
                        <Check size={14} className="text-[var(--color-signal)]" />
                        <span className="text-xs">Approve</span>
                      </Button>
                      <Button
                        variant="secondary"
                        className="!px-3 !py-2"
                        aria-label={`Reject ${task.title}`}
                        title="Reject task"
                        onClick={() => rejectMutation.mutate(task.id)}
                        loading={rejectMutation.isPending && rejectMutation.variables === task.id}
                      >
                        <X size={14} className="text-[var(--color-alert)]" />
                        <span className="text-xs">Reject</span>
                      </Button>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>
      </motion.section>

      <motion.section initial={reduceMotion ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduceMotion ? 0 : 0.3, delay: reduceMotion ? 0 : 0.12 }}>
        <h2 className="text-sm font-medium text-[var(--color-text-primary)] mb-3">
          Awaiting resolution
          <span className="ml-2 text-[var(--color-text-faint)]">({awaitingResolution.length})</span>
        </h2>

        <div className="overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/75 shadow-lg shadow-black/5 backdrop-blur-xl">
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

                  return (
                    <motion.div
                      key={task.id}
                      layout
                      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={reduceMotion ? undefined : { opacity: 0, y: -6 }}
                      transition={{ duration: reduceMotion ? 0 : 0.2 }}
                      className="flex flex-col justify-between gap-3 px-4 py-4 transition-colors hover:bg-[var(--color-surface-hover)]/50 sm:flex-row sm:items-center sm:gap-4 sm:px-5"
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
      </motion.section>
    </div>
  )
}
