import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Calendar, CheckCircle2, Pause, Play, Plus, Trash2, XCircle } from 'lucide-react'
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

export default function CommitScheduler() {
  const orgId = useAuthStore((s) => s.user?.organization_id)
  const queryClient = useQueryClient()

  const [formOpen, setFormOpen] = useState(false)
  const [editingJob, setEditingJob] = useState<CommitJob | null>(null)
  const [detailJobId, setDetailJobId] = useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)

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
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
            Commit Scheduler
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Automate scheduled commits across your repositories
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus size={15} />
          New scheduled commit
        </Button>
      </div>

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
        <div className="flex flex-col gap-3">
          {sortedJobs.map((job) => (
            <Card key={job.id} className="p-5">
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
                    {job.mode === 'guard' && <Badge tone="neutral">guard</Badge>}
                    {job.use_pr && <Badge tone="neutral">via PR</Badge>}
                  </div>
                  <p className="text-xs text-[var(--color-text-muted)] mt-1">
                    {frequencyLabel(job.frequency)} · {job.start_date} → {job.end_date}
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
          ))}
        </div>
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
