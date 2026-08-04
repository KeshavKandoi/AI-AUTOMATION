import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, CheckCircle2, Clock, ExternalLink, Play, Trash2, XCircle } from 'lucide-react'
import { commitSchedulerService, type CommitJobFile, type RunStatus } from '@/services/commitScheduler'
import Modal from '@/components/ui/Modal'
import Badge from '@/components/ui/Badge'
import Skeleton from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
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

function runStatusBadge(status: RunStatus) {
  const map: Record<RunStatus, { tone: 'signal' | 'alert' | 'amber' | 'neutral'; icon: typeof CheckCircle2 }> = {
    success: { tone: 'signal', icon: CheckCircle2 },
    failed: { tone: 'alert', icon: XCircle },
    skipped: { tone: 'amber', icon: Clock },
    pending: { tone: 'neutral', icon: Clock },
  }
  const { tone, icon: Icon } = map[status]
  return (
    <Badge tone={tone}>
      <Icon size={11} className="mr-1 inline" />
      {status}
    </Badge>
  )
}

interface JobDetailDrawerProps {
  open: boolean
  orgId: string
  jobId: string | null
  onClose: () => void
}

export default function JobDetailDrawer({ open, orgId, jobId, onClose }: JobDetailDrawerProps) {
  const queryClient = useQueryClient()
  const [newFileDate, setNewFileDate] = useState('')
  const [newFolder, setNewFolder] = useState('')
  const [newFileName, setNewFileName] = useState('')
  const [newContent, setNewContent] = useState('')

  const { data: job, isLoading, isError } = useQuery({
    queryKey: ['commit-scheduler', 'job', jobId],
    queryFn: () => commitSchedulerService.getJob(jobId!, orgId),
    enabled: open && !!jobId,
  })

  const { data: files, isLoading: filesLoading } = useQuery({
    queryKey: ['commit-scheduler', 'files', jobId],
    queryFn: () => commitSchedulerService.listFiles(jobId!, orgId),
    enabled: open && !!jobId,
  })

  const runNowMutation = useMutation({
    mutationFn: () => commitSchedulerService.runNow(jobId!, orgId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['commit-scheduler', 'job', jobId] })
    },
  })

  const addFileMutation = useMutation({
    mutationFn: () =>
      commitSchedulerService.addFiles(jobId!, orgId, [
        {
          target_date: newFileDate || null,
          folder_path: newFolder,
          file_name: newFileName,
          content: newContent || null,
        },
      ]),
    onSuccess: () => {
      setNewFileDate('')
      setNewFolder('')
      setNewFileName('')
      setNewContent('')
      queryClient.invalidateQueries({ queryKey: ['commit-scheduler', 'files', jobId] })
    },
  })

  const deleteFileMutation = useMutation({
    mutationFn: (fileId: string) => commitSchedulerService.deleteFile(jobId!, orgId, fileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['commit-scheduler', 'files', jobId] })
    },
  })

  return (
    <Modal open={open} onClose={onClose} title={job ? job.repo_full_name : 'Job details'}>
      <div className="flex flex-col gap-6 max-h-[75vh] overflow-y-auto pr-1">
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        ) : isError || !job ? (
          <ErrorBanner message="Couldn't load this job." />
        ) : (
          <>
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="text-sm text-[var(--color-text-muted)]">
                <span className="text-[var(--color-text-primary)]">{job.branch}</span> · {job.frequency} · {job.mode}
                {job.use_pr && ' · via PR'}
              </div>
              <Button
                variant="secondary"
                loading={runNowMutation.isPending}
                onClick={() => runNowMutation.mutate()}
              >
                <Play size={13} />
                Run now
              </Button>
            </div>

            {runNowMutation.isSuccess && (
              <div
                className={
                  runNowMutation.data.status === 'success'
                    ? 'rounded-lg border border-[var(--color-signal-dim)] bg-[var(--color-signal-dim)] px-3 py-2 text-xs text-[var(--color-signal)]'
                    : runNowMutation.data.status === 'failed'
                    ? 'rounded-lg border border-[var(--color-alert-dim)] bg-[var(--color-alert-dim)] px-3 py-2 text-xs text-[var(--color-alert)]'
                    : 'rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-xs text-[var(--color-text-muted)]'
                }
              >
                Run {runNowMutation.data.status}
                {runNowMutation.data.error_message ? ` — ${runNowMutation.data.error_message}` : ''}
              </div>
            )}
            {runNowMutation.isError && <ErrorBanner message="Failed to trigger this run. Try again." />}

            <div>
              <h3 className="text-sm font-medium text-[var(--color-text-primary)] mb-2">Files</h3>
              {job.folder_path && job.file_name && (
                <div className="text-xs text-[var(--color-text-muted)] mb-2">
                  Default (recurring): <span className="font-mono">{job.folder_path}/{job.file_name}</span>
                </div>
              )}
              {filesLoading ? (
                <Skeleton className="h-10 w-full" />
              ) : files && files.length > 0 ? (
                <div className="divide-y divide-[var(--color-border)] border border-[var(--color-border)] rounded-lg">
                  {files.map((f: CommitJobFile) => (
                    <div key={f.id} className="flex items-center justify-between gap-3 px-3 py-2">
                      <div className="text-xs">
                        <span className="font-mono text-[var(--color-text-primary)]">{f.folder_path}/{f.file_name}</span>
                        <span className="text-[var(--color-text-faint)] ml-2">
                          {f.target_date ? f.target_date : 'recurring (every due day)'}
                        </span>
                      </div>
                      <button
                        onClick={() => f.id && deleteFileMutation.mutate(f.id)}
                        className="text-[var(--color-text-faint)] hover:text-[var(--color-alert)] transition-colors"
                        title="Delete file"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState icon={Clock} title="No dated file overrides yet" />
              )}

              <div className="mt-3 grid grid-cols-2 gap-2">
                <Input placeholder="Date (optional)" type="date" value={newFileDate} onChange={(e) => setNewFileDate(e.target.value)} />
                <Input placeholder="Folder path" value={newFolder} onChange={(e) => setNewFolder(e.target.value)} />
                <Input placeholder="File name" value={newFileName} onChange={(e) => setNewFileName(e.target.value)} />
                <Input placeholder="Content (optional)" value={newContent} onChange={(e) => setNewContent(e.target.value)} />
              </div>
              <Button
                variant="secondary"
                className="w-full mt-2"
                disabled={!newFolder.trim() || !newFileName.trim()}
                loading={addFileMutation.isPending}
                onClick={() => addFileMutation.mutate()}
              >
                Add file
              </Button>
            </div>

            <div>
              <h3 className="text-sm font-medium text-[var(--color-text-primary)] mb-2">Run history</h3>
              {job.runs.length === 0 ? (
                <EmptyState icon={Clock} title="No runs yet" />
              ) : (
                <div className="divide-y divide-[var(--color-border)] border border-[var(--color-border)] rounded-lg">
                  {job.runs.map((run) => (
                    <div key={run.id} className="flex items-center justify-between gap-3 px-3 py-2">
                      <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
                        <span>{run.run_date}</span>
                        {runStatusBadge(run.status)}
                        {run.error_message && (
                          <span className="text-[var(--color-alert)] truncate max-w-[220px]">{run.error_message}</span>
                        )}
                      </div>
                      {run.commit_url && (
                        <a href={run.commit_url} target="_blank" rel="noreferrer" className="text-[var(--color-signal)] hover:underline flex items-center gap-1 text-xs shrink-0">
                          View <ExternalLink size={11} />
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </Modal>
  )
}
