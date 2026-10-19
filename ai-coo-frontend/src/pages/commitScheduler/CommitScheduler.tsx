import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, useReducedMotion } from 'framer-motion'
import { AlertCircle, Calendar, CheckCircle2, Pause, Play, Plus, RotateCw, Trash2, XCircle } from 'lucide-react'
import { commitSchedulerService, type CommitJob, type JobStatus } from '@/services/commitScheduler'
import { useAuthStore } from '@/store/authStore'
import Card from '@/components/ui/Card'
import Skeleton from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import Badge from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import JobFormModal from './JobFormModal'
import JobDetailDrawer from './JobDetailDrawer'

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-[var(--color-alert-dim)] bg-[var(--color-alert-dim)] px-3 py-2 text-xs text-[var(--color-alert)]">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

function statusBadge(status: JobStatus) {
  const map: Record<JobStatus, { tone: 'signal' | 'alert' | 'amber' | 'neutral'; icon: typeof CheckCircle2 }> = {
    active: { tone: 'signal', icon: CheckCircle2 },
    paused: { tone: 'amber', icon: Pause },
    completed: { tone: 'neutral', icon: CheckCircle2 },
    cancelled: { tone: 'alert', icon: XCircle },
  }
  const { tone, icon: Icon } = map[status]
  return (
    <Badge tone={tone}>
      <Icon size={11} className="mr-1 inline" />
      {status}
    </Badge>
  )
}

function frequencyLabel(freq: string) {
  const map: Record<string, string> = {
    daily: 'Daily',
    every_2_days: 'Every 2 days',
    weekdays: 'Weekdays',
    custom: 'Custom dates',
  }
  return map[freq] ?? freq
}

function scheduleSummary(job: CommitJob) {
  if (job.mode === 'scheduled') {
    return job.execution_at ? `One-time · runs ${new Date(job.execution_at).toLocaleString()}` : 'One-time'
  }
  return `${frequencyLabel(job.frequency)} · ${job.start_date} → ${job.end_date}`
}

type JobFilter = 'all' | 'active' | 'paused' | 'finished'

export default function CommitScheduler() {
  const reduceMotion = useReducedMotion()
  const orgId = useAuthStore((s) => s.user?.organization_id)
  const queryClient = useQueryClient()

  const [formOpen, setFormOpen] = useState(false)
  const [editingJob, setEditingJob] = useState<CommitJob | null>(null)
  const [detailJobId, setDetailJobId] = useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [jobFilter, setJobFilter] = useState<JobFilter>('all')

  const {
    data: jobs,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['commit-scheduler', 'jobs', orgId],
    queryFn: () => commitSchedulerService.listJobs(orgId!),
    enabled: !!orgId,
  })

  const toggleStatusMutation = useMutation({
    mutationFn: ({ job, status }: { job: CommitJob; status: JobStatus }) =>
      commitSchedulerService.updateJob(job.id, orgId!, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['commit-scheduler', 'jobs'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (jobId: string) => commitSchedulerService.deleteJob(jobId, orgId!),
    onSuccess: () => {
      setConfirmDeleteId(null)
      queryClient.invalidateQueries({ queryKey: ['commit-scheduler', 'jobs'] })
    },
  })

  const sortedJobs = useMemo(() => {
    if (!jobs) return []
    const order: Record<JobStatus, number> = { active: 0, paused: 1, completed: 2, cancelled: 3 }
    return [...jobs].sort((a, b) => order[a.status] - order[b.status])
  }, [jobs])

  const visibleJobs = useMemo(() => {
    if (jobFilter === 'all') return sortedJobs
    if (jobFilter === 'finished') return sortedJobs.filter((job) => job.status === 'completed' || job.status === 'cancelled')
    return sortedJobs.filter((job) => job.status === jobFilter)
  }, [jobFilter, sortedJobs])

  const jobCounts = useMemo(() => ({
    all: jobs?.length ?? 0,
    active: jobs?.filter((job) => job.status === 'active').length ?? 0,
    paused: jobs?.filter((job) => job.status === 'paused').length ?? 0,
    finished: jobs?.filter((job) => job.status === 'completed' || job.status === 'cancelled').length ?? 0,
  }), [jobs])

  const openCreate = () => {
    setEditingJob(null)
    setFormOpen(true)
  }

  const openEdit = (job: CommitJob) => {
    setEditingJob(job)
    setFormOpen(true)
  }

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto flex flex-col gap-6">
      <motion.header initial={reduceMotion ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduceMotion ? 0 : 0.35 }} className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-2xl border border-[var(--color-signal)]/20 bg-[var(--color-signal-dim)] text-[var(--color-signal)]">
              <Calendar size={20} />
            </span>
            <div>
              <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
                Commit Scheduler
              </h1>
              <p className="mt-1 text-sm text-[var(--color-text-muted)]">
                Automate scheduled commits across your repositories
              </p>
            </div>
          </div>
        </div>
        <Button onClick={openCreate}>
          <Plus size={15} />
          New scheduled commit
        </Button>
      </motion.header>

      {!isLoading && !isError && jobs && jobs.length > 0 && (
        <motion.section
          initial={reduceMotion ? false : { opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: reduceMotion ? 0 : 0.3, delay: reduceMotion ? 0 : 0.06 }}
          aria-label="Scheduled commit overview"
          className="grid grid-cols-1 gap-3 sm:grid-cols-3"
        >
          {([
            { label: 'Total schedules', value: jobCounts.all, icon: Calendar, tone: 'text-[var(--color-text-primary)]', wash: 'bg-[var(--color-surface-hover)]' },
            { label: 'Running', value: jobCounts.active, icon: RotateCw, tone: 'text-[var(--color-signal)]', wash: 'bg-[var(--color-signal-dim)]' },
            { label: 'Paused', value: jobCounts.paused, icon: Pause, tone: 'text-[var(--color-amber)]', wash: 'bg-[var(--color-amber-dim)]' },
          ]).map(({ label, value, icon: Icon, tone, wash }, index) => (
            <motion.div
              key={label}
              initial={reduceMotion ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: reduceMotion ? 0 : 0.28, delay: reduceMotion ? 0 : index * 0.05 }}
              className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4"
            >
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium text-[var(--color-text-muted)]">{label}</p>
                <span className={`grid h-8 w-8 place-items-center rounded-xl ${wash} ${tone}`}><Icon size={15} /></span>
              </div>
              <p className={`mt-3 text-2xl font-semibold tabular-nums ${tone}`}>{value}</p>
            </motion.div>
          ))}
        </motion.section>
      )}

      {isLoading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : isError ? (
        <ErrorBanner message="Couldn't load scheduled commits." />
      ) : sortedJobs.length === 0 ? (
        <Card className="p-8">
          <EmptyState
            icon={Calendar}
            title="No scheduled commits yet"
            description="Create one to automatically commit files to a repository on a schedule."
          />
        </Card>
      ) : (
        <section aria-label="Scheduled commits" className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">Your schedules</h2>
              <p className="mt-1 text-xs text-[var(--color-text-faint)]">Manage upcoming and completed commit runs</p>
            </div>
            <div className="flex items-center gap-1 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-1" role="group" aria-label="Filter schedules">
              {([
                ['all', 'All'], ['active', 'Running'], ['paused', 'Paused'], ['finished', 'Finished'],
              ] as const).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={jobFilter === value}
                  onClick={() => setJobFilter(value)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${jobFilter === value ? 'bg-[var(--color-signal-dim)] text-[var(--color-signal)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'}`}
                >
                  {label}<span className="ml-1.5 opacity-70">{jobCounts[value]}</span>
                </button>
              ))}
            </div>
          </div>

          {visibleJobs.length === 0 ? (
            <Card className="p-6 text-center text-sm text-[var(--color-text-muted)]">
              No {jobFilter} schedules to show.
            </Card>
          ) : (
            <motion.div layout className="flex flex-col gap-3">
              {visibleJobs.map((job, index) => (
                <motion.div
                  key={job.id}
                  layout
                  initial={reduceMotion ? false : { opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: reduceMotion ? 0 : 0.28, delay: reduceMotion ? 0 : Math.min(index * 0.045, 0.24), layout: { duration: 0.2 } }}
                  whileHover={reduceMotion ? undefined : { y: -2 }}
                >
                  <Card className="p-5 transition-colors hover:border-[var(--color-border-hover)]">
                    <div className="flex items-start justify-between gap-4 flex-wrap">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <button
                            onClick={() => setDetailJobId(job.id)}
                            className="text-sm font-medium text-[var(--color-text-primary)] hover:underline"
                          >
                            {job.repo_full_name}
                          </button>
                          <span className="text-xs text-[var(--color-text-faint)]">→ {job.branch}</span>
                          {statusBadge(job.status)}
                          {job.mode === 'scheduled' && <Badge tone="neutral">one-time</Badge>}
                          {job.mode === 'guard' && <Badge tone="neutral">guard</Badge>}
                          {job.use_pr && <Badge tone="neutral">via PR</Badge>}
                        </div>
                        <p className="text-xs text-[var(--color-text-muted)] mt-1">
                          {scheduleSummary(job)}
                        </p>
                        {job.folder_path && job.file_name && (
                          <p className="text-xs text-[var(--color-text-faint)] mt-1 font-mono">
                            {job.folder_path}/{job.file_name}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Button variant="ghost" onClick={() => setDetailJobId(job.id)}>
                          <Play size={13} />
                          Details
                        </Button>
                        <Button variant="ghost" onClick={() => openEdit(job)}>
                          Edit
                        </Button>
                        {job.status === 'active' ? (
                          <Button
                            variant="ghost"
                            loading={toggleStatusMutation.isPending}
                            onClick={() => toggleStatusMutation.mutate({ job, status: 'paused' })}
                          >
                            <Pause size={13} />
                            Pause
                          </Button>
                        ) : job.status === 'paused' ? (
                          <Button
                            variant="ghost"
                            loading={toggleStatusMutation.isPending}
                            onClick={() => toggleStatusMutation.mutate({ job, status: 'active' })}
                          >
                            <Play size={13} />
                            Resume
                          </Button>
                        ) : null}
                        {confirmDeleteId === job.id ? (
                          <Button
                            variant="primary"
                            className="!bg-[var(--color-alert)] !text-white"
                            loading={deleteMutation.isPending}
                            onBlur={() => setConfirmDeleteId(null)}
                            onClick={() => deleteMutation.mutate(job.id)}
                          >
                            Confirm?
                          </Button>
                        ) : (
                          <button
                            onClick={() => setConfirmDeleteId(job.id)}
                            className="text-[var(--color-text-faint)] hover:text-[var(--color-alert)] transition-colors p-2"
                            title="Delete job"
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                      </div>
                    </div>
                  </Card>
                </motion.div>
              ))}
            </motion.div>
          )}
        </section>
      )}

      <JobFormModal
        open={formOpen}
        orgId={orgId ?? ''}
        job={editingJob}
        onClose={() => setFormOpen(false)}
        onSuccess={() => setFormOpen(false)}
      />

      <JobDetailDrawer
        open={!!detailJobId}
        orgId={orgId ?? ''}
        jobId={detailJobId}
        onClose={() => setDetailJobId(null)}
      />
    </div>
  )
}
