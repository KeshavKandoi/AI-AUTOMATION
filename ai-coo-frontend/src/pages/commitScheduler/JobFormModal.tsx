import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle } from 'lucide-react'
import { commitSchedulerService, type CommitJob, type Frequency, type JobMode } from '@/services/commitScheduler'
import Modal from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-[var(--color-alert-dim)] bg-[var(--color-alert-dim)] px-3 py-2 text-xs text-[var(--color-alert)]">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

function selectClass() {
  return 'w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)] disabled:opacity-50 disabled:cursor-not-allowed'
}

function labelClass() {
  return 'text-sm font-medium text-[var(--color-text-muted)]'
}

function pad(n: number) {
  return String(n).padStart(2, '0')
}

function toLocalDateTimeValue(d: Date) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function toLocalDateValue(d: Date) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

interface JobFormModalProps {
  open: boolean
  orgId: string
  job: CommitJob | null
  onClose: () => void
  onSuccess: () => void
  initialValues?: {
    repoFullName?: string
    usePr?: boolean
    commitMessage?: string
  }
}

export default function JobFormModal({ open, orgId, job, onClose, onSuccess, initialValues }: JobFormModalProps) {
  const isEdit = !!job
  const queryClient = useQueryClient()

  const [repoFullName, setRepoFullName] = useState('')
  const [branch, setBranch] = useState('')
  const [folderPath, setFolderPath] = useState('')
  const [fileName, setFileName] = useState('')
  const [fileContent, setFileContent] = useState('')
  const [commitMessage, setCommitMessage] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [frequency, setFrequency] = useState<Frequency>('daily')
  const [customDates, setCustomDates] = useState('')
  const [executionAt, setExecutionAt] = useState('')
  const [mode, setMode] = useState<JobMode>('scheduled')
  const [guardCutoff, setGuardCutoff] = useState('23:30:00')
  const [usePr, setUsePr] = useState(false)
  const [status, setStatus] = useState(job?.status ?? 'active')

  const minExecutionAt = useMemo(
    () => toLocalDateTimeValue(new Date(Date.now() + 60_000)),
    [open]
  )
  const todayStr = useMemo(() => toLocalDateValue(new Date()), [open])

  useEffect(() => {
    if (job) {
      setRepoFullName(job.repo_full_name)
      setBranch(job.branch)
      setFolderPath(job.folder_path ?? '')
      setFileName(job.file_name ?? '')
      setFileContent(job.file_content ?? '')
      setCommitMessage(job.commit_message)
      setStartDate(job.start_date ?? '')
      setEndDate(job.end_date ?? '')
      setFrequency(job.frequency)
      setCustomDates((job.custom_dates ?? []).join(', '))
      setExecutionAt(job.execution_at ? toLocalDateTimeValue(new Date(job.execution_at)) : '')
      setMode(job.mode)
      setGuardCutoff(job.guard_cutoff_time)
      setUsePr(job.use_pr)
      setStatus(job.status)
    } else {
      setRepoFullName(initialValues?.repoFullName ?? '')
      setBranch('')
      setFolderPath('')
      setFileName('')
      setFileContent('')
      setCommitMessage(initialValues?.commitMessage ?? '')
      setStartDate('')
      setEndDate('')
      setFrequency('daily')
      setCustomDates('')
      setExecutionAt('')
      setMode('scheduled')
      setGuardCutoff('23:30:00')
      setUsePr(initialValues?.usePr ?? false)
      setStatus('active')
    }
  }, [job, open, initialValues])

  const { data: repos, isLoading: reposLoading, isError: reposError } = useQuery({
    queryKey: ['commit-scheduler', 'repos', orgId],
    queryFn: () => commitSchedulerService.listRepos(orgId),
    enabled: open && !isEdit,
  })

  const { data: branches, isLoading: branchesLoading } = useQuery({
    queryKey: ['commit-scheduler', 'branches', orgId, repoFullName],
    queryFn: () => commitSchedulerService.listBranches(orgId, repoFullName),
    enabled: open && !isEdit && !!repoFullName,
  })

  const parsedCustomDates = useMemo(
    () =>
      customDates
        .split(',')
        .map((d) => d.trim())
        .filter(Boolean),
    [customDates]
  )

  const createMutation = useMutation({
    mutationFn: () =>
      commitSchedulerService.createJob({
        organization_id: orgId,
        repo_full_name: repoFullName,
        branch,
        folder_path: folderPath || undefined,
        file_name: fileName || undefined,
        file_content: fileContent || undefined,
        commit_message: commitMessage,
        mode,
        use_pr: usePr,
        ...(mode === 'scheduled'
          ? { execution_at: new Date(executionAt).toISOString() }
          : {
              start_date: startDate,
              end_date: endDate,
              frequency,
              custom_dates: frequency === 'custom' ? parsedCustomDates : undefined,
              ...(mode === 'guard' ? { guard_cutoff_time: guardCutoff } : {}),
            }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['commit-scheduler', 'jobs'] })
      onSuccess()
    },
  })

  const updateMutation = useMutation({
    mutationFn: () =>
      commitSchedulerService.updateJob(job!.id, orgId, {
        branch,
        folder_path: folderPath || undefined,
        file_name: fileName || undefined,
        file_content: fileContent || undefined,
        commit_message: commitMessage,
        ...(mode === 'scheduled'
          ? { execution_at: executionAt ? new Date(executionAt).toISOString() : undefined }
          : {
              start_date: startDate,
              end_date: endDate,
              frequency,
              custom_dates: frequency === 'custom' ? parsedCustomDates : undefined,
            }),
        status,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['commit-scheduler', 'jobs'] })
      onSuccess()
    },
  })

  const mutation = isEdit ? updateMutation : createMutation
  const canSubmit =
    (isEdit || (repoFullName.trim() && branch.trim())) &&
    commitMessage.trim() &&
    (mode === 'scheduled'
      ? !!executionAt
      : !!(startDate && endDate) && (frequency !== 'custom' || parsedCustomDates.length > 0))

  return (
    <Modal open={open} onClose={onClose} title={isEdit ? 'Edit scheduled commit' : 'New scheduled commit'}>
      <div className="flex flex-col gap-4 max-h-[70vh] overflow-y-auto pr-1">
        <div className="flex flex-col gap-1.5">
          <label className={labelClass()}>Repository</label>
          {isEdit ? (
            <Input value={repoFullName} disabled />
          ) : (
            <select value={repoFullName} onChange={(e) => { setRepoFullName(e.target.value); setBranch('') }} className={selectClass()}>
              <option value="">{reposLoading ? 'Loading repos...' : 'Select a repository'}</option>
              {repos?.map((r) => (
                <option key={r.full_name} value={r.full_name}>{r.full_name}</option>
              ))}
            </select>
          )}
          {reposError && <ErrorBanner message="Couldn't load repositories." />}
        </div>

        <div className="flex flex-col gap-1.5">
          <label className={labelClass()}>Branch</label>
          {isEdit ? (
            <select value={branch} onChange={(e) => setBranch(e.target.value)} className={selectClass()}>
              <option value={job!.branch}>{job!.branch}</option>
            </select>
          ) : (
            <select
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              disabled={!repoFullName}
              className={selectClass()}
            >
              <option value="">{branchesLoading ? 'Loading branches...' : 'Select a branch'}</option>
              {branches?.map((b) => (
                <option key={b.name} value={b.name}>{b.name}</option>
              ))}
            </select>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Input label="Folder path" placeholder="e.g. logs" value={folderPath} onChange={(e) => setFolderPath(e.target.value)} />
          <Input label="File name" placeholder="e.g. update.md" value={fileName} onChange={(e) => setFileName(e.target.value)} />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className={labelClass()}>Default file content (optional)</label>
          <textarea
            value={fileContent}
            onChange={(e) => setFileContent(e.target.value)}
            rows={3}
            placeholder="Used when no dated file overrides this run"
            className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-faint)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)] resize-none font-mono"
          />
        </div>

        <Input label="Commit message" placeholder="Auto-commit" value={commitMessage} onChange={(e) => setCommitMessage(e.target.value)} />

        <div className="flex flex-col gap-1.5">
          <label className={labelClass()}>Mode</label>
          <select value={mode} onChange={(e) => setMode(e.target.value as JobMode)} disabled={isEdit} className={selectClass()}>
            <option value="scheduled">Scheduled — runs once at an exact date & time</option>
            <option value="recurring">Recurring — runs on a repeating schedule</option>
            <option value="guard">Guard — safety net, commits only if you haven't already</option>
          </select>
        </div>

        {mode === 'scheduled' ? (
          <div className="flex flex-col gap-1.5">
            <label className={labelClass()}>Execution date & time</label>
            <input
              type="datetime-local"
              value={executionAt}
              min={minExecutionAt}
              onChange={(e) => setExecutionAt(e.target.value)}
              className={selectClass()}
            />
            <p className="text-xs text-[var(--color-text-faint)]">
              This job runs once, automatically, at this exact date and time — then marks itself complete.
            </p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Start date"
                type="date"
                value={startDate}
                min={todayStr}
                onChange={(e) => setStartDate(e.target.value)}
              />
              <Input
                label="End date"
                type="date"
                value={endDate}
                min={startDate || todayStr}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className={labelClass()}>Frequency</label>
              <select value={frequency} onChange={(e) => setFrequency(e.target.value as Frequency)} className={selectClass()}>
                <option value="daily">Daily</option>
                <option value="every_2_days">Every 2 days</option>
                <option value="weekdays">Weekdays only</option>
                <option value="custom">Custom dates</option>
              </select>
            </div>

            {frequency === 'custom' && (
              <Input
                label="Custom dates (comma-separated, YYYY-MM-DD)"
                placeholder="2026-08-10, 2026-08-14"
                value={customDates}
                onChange={(e) => setCustomDates(e.target.value)}
              />
            )}

            {mode === 'guard' && (
              <>
                <Input
                  label="Guard cutoff time"
                  type="time"
                  step={1}
                  value={guardCutoff}
                  onChange={(e) => setGuardCutoff(e.target.value)}
                  disabled={isEdit}
                />
                <p className="text-xs text-[var(--color-text-faint)] -mt-2">
                  On each due day: if a real commit already landed before {guardCutoff.slice(0, 5)}, nothing happens.
                  Otherwise AI COO commits automatically right at the cutoff.
                </p>
              </>
            )}
          </>
        )}

        <label className="flex items-center gap-2 text-sm text-[var(--color-text-muted)]">
          <input type="checkbox" checked={usePr} disabled={isEdit} onChange={(e) => setUsePr(e.target.checked)} className="accent-[var(--color-signal)]" />
          Open a pull request instead of committing directly to {branch || 'the branch'}
        </label>
        {isEdit && (
          <p className="text-xs text-[var(--color-text-faint)] -mt-2">
            Repository, mode, PR setting, and guard cutoff can't be changed after creation — delete and recreate the job if these need to change.
          </p>
        )}

        {isEdit && (
          <div className="flex flex-col gap-1.5">
            <label className={labelClass()}>Status</label>
            <select value={status} onChange={(e) => setStatus(e.target.value as CommitJob['status'])} className={selectClass()}>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        )}

        {mutation.isError && (
          <ErrorBanner
            message={
              (mutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
              'Something went wrong. Please check the fields and try again.'
            }
          />
        )}

        <Button className="w-full" disabled={!canSubmit} loading={mutation.isPending} onClick={() => mutation.mutate()}>
          {isEdit ? 'Save changes' : 'Create scheduled commit'}
        </Button>
      </div>
    </Modal>
  )
}
