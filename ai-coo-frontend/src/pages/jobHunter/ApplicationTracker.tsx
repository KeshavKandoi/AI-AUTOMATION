import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle,
  Briefcase,
  Building2,
  Calendar,
  Download,
  ExternalLink,
  MapPin,
  Paperclip,
  Plus,
  StickyNote,
  Trash2,
} from 'lucide-react'
import { jobHunterService } from '@/services/jobHunter'
import type { ApplicationRow, ApplicationStatus, AttachmentType } from '@/services/jobHunter'
import Card from '@/components/ui/Card'
import Skeleton from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import Badge from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import Modal from '@/components/ui/Modal'
import { cn } from '@/lib/utils'

const STATUS_OPTIONS: { value: ApplicationStatus; label: string }[] = [
  { value: 'saved', label: 'Saved' },
  { value: 'applied', label: 'Applied' },
  { value: 'assessment', label: 'Assessment' },
  { value: 'interview', label: 'Interview' },
  { value: 'hr_round', label: 'HR Round' },
  { value: 'technical_round', label: 'Technical Round' },
  { value: 'final_round', label: 'Final Round' },
  { value: 'offer', label: 'Offer' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'archived', label: 'Archived' },
]

const ATTACHMENT_TYPES: { value: AttachmentType; label: string }[] = [
  { value: 'resume', label: 'Resume' },
  { value: 'cover_letter', label: 'Cover letter' },
  { value: 'assignment', label: 'Assignment' },
  { value: 'interview_notes', label: 'Interview notes' },
  { value: 'offer_letter', label: 'Offer letter' },
  { value: 'other', label: 'Other' },
]

function statusLabel(status: string): string {
  return STATUS_OPTIONS.find((s) => s.value === status)?.label ?? status.replace(/_/g, ' ')
}

function statusTone(status: string): 'signal' | 'alert' | 'amber' | 'neutral' {
  if (status === 'offer') return 'signal'
  if (status === 'rejected') return 'alert'
  if (status === 'archived' || status === 'saved') return 'neutral'
  return 'amber'
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-[var(--color-alert-dim)] bg-[var(--color-alert-dim)] px-3 py-2 text-xs text-[var(--color-alert)]">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

function selectClass() {
  return 'rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)]'
}

function formatDate(iso: string | null): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function ApplicationCard({ row, onOpen }: { row: ApplicationRow; onOpen: () => void }) {
  const { data: job, isLoading } = useQuery({
    queryKey: ['job-hunter', 'job', row.job_id],
    queryFn: () => jobHunterService.getJob(row.job_id),
    staleTime: 5 * 60 * 1000,
  })

  return (
    <Card
      className="p-5 cursor-pointer hover:border-[var(--color-border-hover)] transition-colors"
      onClick={onOpen}
    >
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          {isLoading ? (
            <Skeleton className="h-4 w-48" />
          ) : job ? (
            <>
              <h3 className="text-sm font-medium text-[var(--color-text-primary)]">{job.job_title}</h3>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5 text-xs text-[var(--color-text-muted)]">
                <span className="flex items-center gap-1">
                  <Building2 size={12} />
                  {job.company_name}
                </span>
                {job.location && (
                  <span className="flex items-center gap-1">
                    <MapPin size={12} />
                    {job.location}
                  </span>
                )}
              </div>
            </>
          ) : (
            <span className="text-sm text-[var(--color-text-faint)]">Job unavailable</span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Badge tone={statusTone(row.status)}>{statusLabel(row.status)}</Badge>
        </div>
      </div>
      <div className="flex items-center gap-3 mt-3 text-xs text-[var(--color-text-faint)]">
        {row.applied_at && (
          <span className="flex items-center gap-1">
            <Calendar size={11} />
            Applied {formatDate(row.applied_at)}
          </span>
        )}
        <span>Updated {formatDate(row.updated_at)}</span>
      </div>
    </Card>
  )
}

function ApplicationDetailModal({ applicationId, onClose }: { applicationId: string; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [noteDraft, setNoteDraft] = useState('')
  const [reminderDate, setReminderDate] = useState('')
  const [reminderNote, setReminderNote] = useState('')
  const [attachmentType, setAttachmentType] = useState<AttachmentType>('resume')
  const [attachmentFile, setAttachmentFile] = useState<File | null>(null)

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['job-hunter', 'application', applicationId] })
  }

  const { data: application, isLoading, isError } = useQuery({
    queryKey: ['job-hunter', 'application', applicationId],
    queryFn: () => jobHunterService.getApplication(applicationId),
  })

  const statusMutation = useMutation({
    mutationFn: (status: ApplicationStatus) => jobHunterService.updateApplicationStatus(applicationId, status),
    onSuccess: () => {
      invalidate()
      queryClient.invalidateQueries({ queryKey: ['job-hunter', 'applications'] })
    },
  })

  const noteMutation = useMutation({
    mutationFn: (content: string) => jobHunterService.addNote(applicationId, content),
    onSuccess: () => {
      setNoteDraft('')
      invalidate()
    },
  })

  const reminderMutation = useMutation({
    mutationFn: () =>
      jobHunterService.createReminder(
        applicationId,
        new Date(reminderDate).toISOString(),
        reminderNote || undefined
      ),
    onSuccess: () => {
      setReminderDate('')
      setReminderNote('')
      invalidate()
    },
  })

  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!attachmentFile) throw new Error('No file selected')
      return jobHunterService.addAttachment(applicationId, attachmentFile, attachmentType)
    },
    onSuccess: () => {
      setAttachmentFile(null)
      invalidate()
    },
  })

  const deleteAttachmentMutation = useMutation({
    mutationFn: (attachmentId: string) => jobHunterService.deleteAttachment(applicationId, attachmentId),
    onSuccess: () => invalidate(),
  })

  const downloadMutation = useMutation({
    mutationFn: (attachmentId: string) => jobHunterService.getAttachmentDownloadUrl(applicationId, attachmentId),
    onSuccess: (url) => window.open(url, '_blank'),
  })

  return (
    <Modal open onClose={onClose} title={application?.job?.job_title ?? 'Application'} className="max-w-2xl">
      <div className="flex flex-col gap-6 max-h-[75vh] overflow-y-auto pr-1">
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        ) : isError || !application ? (
          <ErrorBanner message="Couldn't load this application." />
        ) : (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[var(--color-text-muted)]">
                {application.job && (
                  <>
                    <span className="flex items-center gap-1">
                      <Building2 size={12} />
                      {application.job.company_name}
                    </span>
                    {application.job.location && (
                      <span className="flex items-center gap-1">
                        <MapPin size={12} />
                        {application.job.location}
                      </span>
                    )}
                    
                      href={application.job.original_apply_url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1 text-[var(--color-signal)] hover:underline"
                    >
                      Original listing
                      <ExternalLink size={11} />
                    </a>
                  </>
                )}
              </div>
              <select
                value={application.status}
                disabled={statusMutation.isPending}
                onChange={(e) => statusMutation.mutate(e.target.value as ApplicationStatus)}
                className={selectClass()}
              >
                {STATUS_OPTIONS.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
            {statusMutation.isError && <ErrorBanner message="Couldn't update status. Try again." />}

            <div>
              <h3 className="text-sm font-medium text-[var(--color-text-primary)] mb-2 flex items-center gap-1.5">
                <StickyNote size={14} />
                Notes
              </h3>
              {application.notes.length === 0 ? (
                <p className="text-xs text-[var(--color-text-faint)]">No notes yet.</p>
              ) : (
                <div className="flex flex-col gap-2 mb-3">
                  {application.notes.map((n) => (
                    <div key={n.id} className="rounded-lg border border-[var(--color-border)] p-3">
                      <p className="text-sm text-[var(--color-text-primary)] whitespace-pre-wrap">{n.content}</p>
                      <p className="text-[11px] text-[var(--color-text-faint)] mt-1">{formatDateTime(n.created_at)}</p>
                    </div>
                  ))}
                </div>
              )}
              <div className="flex gap-2">
                <textarea
                  value={noteDraft}
                  onChange={(e) => setNoteDraft(e.target.value)}
                  placeholder="Add a private note…"
                  rows={2}
                  className="flex-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-faint)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)] resize-none"
                />
                <Button
                  variant="secondary"
                  disabled={!noteDraft.trim()}
                  loading={noteMutation.isPending}
                  onClick={() => noteMutation.mutate(noteDraft.trim())}
                >
                  Add
                </Button>
              </div>
              {noteMutation.isError && <ErrorBanner message="Couldn't add note." />}
            </div>

            <div>
              <h3 className="text-sm font-medium text-[var(--color-text-primary)] mb-2 flex items-center gap-1.5">
                <Calendar size={14} />
                Reminders
              </h3>
              {application.reminders.length === 0 ? (
                <p className="text-xs text-[var(--color-text-faint)] mb-2">No reminders set.</p>
              ) : (
                <div className="flex flex-col gap-2 mb-3">
                  {application.reminders.map((r) => (
                    <div key={r.id} className="flex items-center justify-between rounded-lg border border-[var(--color-border)] px-3 py-2">
                      <div className="text-xs">
                        <span className="text-[var(--color-text-primary)]">{formatDateTime(r.remind_at)}</span>
                        {r.note && <span className="text-[var(--color-text-muted)] ml-2">{r.note}</span>}
                      </div>
                      <Badge tone={r.status === 'pending' ? 'amber' : 'neutral'}>{r.status}</Badge>
                    </div>
                  ))}
                </div>
              )}
              <div className="grid grid-cols-[1fr_1fr_auto] gap-2">
                <Input
                  type="datetime-local"
                  value={reminderDate}
                  onChange={(e) => setReminderDate(e.target.value)}
                />
                <Input
                  placeholder="Note (optional)"
                  value={reminderNote}
                  onChange={(e) => setReminderNote(e.target.value)}
                />
                <Button
                  variant="secondary"
                  disabled={!reminderDate}
                  loading={reminderMutation.isPending}
                  onClick={() => reminderMutation.mutate()}
                >
                  <Plus size={14} />
                </Button>
              </div>
              {reminderMutation.isError && <ErrorBanner message="Couldn't create reminder." />}
            </div>

            <div>
              <h3 className="text-sm font-medium text-[var(--color-text-primary)] mb-2 flex items-center gap-1.5">
                <Paperclip size={14} />
                Attachments
              </h3>
              {application.attachments.length === 0 ? (
                <p className="text-xs text-[var(--color-text-faint)] mb-2">No attachments yet.</p>
              ) : (
                <div className="flex flex-col gap-2 mb-3">
                  {application.attachments.map((a) => (
                    <div key={a.id} className="flex items-center justify-between rounded-lg border border-[var(--color-border)] px-3 py-2">
                      <div className="text-xs min-w-0">
                        <span className="text-[var(--color-text-primary)] truncate">{a.file_name}</span>
                        <span className="text-[var(--color-text-faint)] ml-2">{a.file_type}</span>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          onClick={() => downloadMutation.mutate(a.id)}
                          className="text-[var(--color-text-faint)] hover:text-[var(--color-signal)] transition-colors"
                          title="Download"
                        >
                          <Download size={13} />
                        </button>
                        <button
                          onClick={() => deleteAttachmentMutation.mutate(a.id)}
                          className="text-[var(--color-text-faint)] hover:text-[var(--color-alert)] transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <div className="flex flex-wrap items-center gap-2">
                <select
                  value={attachmentType}
                  onChange={(e) => setAttachmentType(e.target.value as AttachmentType)}
                  className={selectClass()}
                >
                  {ATTACHMENT_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
                <input
                  type="file"
                  onChange={(e) => setAttachmentFile(e.target.files?.[0] ?? null)}
                  className="text-xs text-[var(--color-text-muted)] flex-1 min-w-[160px]"
                />
                <Button
                  variant="secondary"
                  disabled={!attachmentFile}
                  loading={uploadMutation.isPending}
                  onClick={() => uploadMutation.mutate()}
                >
                  Upload
                </Button>
              </div>
              {uploadMutation.isError && <ErrorBanner message="Couldn't upload attachment." />}
            </div>

            {application.activity.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-[var(--color-text-primary)] mb-2">Activity</h3>
                <div className="flex flex-col gap-1.5">
                  {application.activity.map((ev) => (
                    <div key={ev.id} className="text-xs text-[var(--color-text-muted)] flex items-center gap-2">
                      <span className="text-[var(--color-text-faint)] shrink-0">{formatDateTime(ev.created_at)}</span>
                      <span>{ev.summary}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </Modal>
  )
}

export default function ApplicationTracker() {
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | 'all'>('all')
  const [openId, setOpenId] = useState<string | null>(null)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['job-hunter', 'applications', statusFilter],
    queryFn: () => jobHunterService.listApplications(statusFilter === 'all' ? undefined : statusFilter),
  })

  const rows = data ?? []

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setStatusFilter('all')}
          className={cn(
            'rounded-lg px-3 py-1.5 text-xs border transition-colors',
            statusFilter === 'all'
              ? 'border-[var(--color-signal)] bg-[var(--color-signal-dim)] text-[var(--color-signal)]'
              : 'border-[var(--color-border)] text-[var(--color-text-muted)] hover:border-[var(--color-border-hover)]'
          )}
        >
          All
        </button>
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s.value}
            onClick={() => setStatusFilter(s.value)}
            className={cn(
              'rounded-lg px-3 py-1.5 text-xs border transition-colors',
              statusFilter === s.value
                ? 'border-[var(--color-signal)] bg-[var(--color-signal-dim)] text-[var(--color-signal)]'
                : 'border-[var(--color-border)] text-[var(--color-text-muted)] hover:border-[var(--color-border-hover)]'
            )}
          >
            {s.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-3">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : isError ? (
        <Card className="p-6">
          <ErrorBanner message="Couldn't load applications." />
          <Button variant="ghost" className="mt-3" onClick={() => refetch()}>
            Retry
          </Button>
        </Card>
      ) : rows.length === 0 ? (
        <Card className="p-8">
          <EmptyState
            icon={Briefcase}
            title="No applications yet"
            description="Save jobs from Discover to start tracking them here."
          />
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {rows.map((row) => (
            <ApplicationCard key={row.id} row={row} onOpen={() => setOpenId(row.id)} />
          ))}
        </div>
      )}

      {openId && <ApplicationDetailModal applicationId={openId} onClose={() => setOpenId(null)} />}
    </div>
  )
}
