import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle, ChevronDown, ChevronRight, Clock, ExternalLink } from 'lucide-react'
import { auditLogsService } from '@/services/audit-logs'
import Modal from '@/components/ui/Modal'
import Badge from '@/components/ui/Badge'
import Skeleton from '@/components/ui/Skeleton'
import { getModuleIcon, getModuleLabel, getStatusTone, formatActionLabel } from '@/lib/auditLogDisplay'

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-[var(--color-alert-dim)] bg-[var(--color-alert-dim)] px-3 py-2 text-xs text-[var(--color-alert)]">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  if (value === null || value === undefined || value === '') return null
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-[var(--color-text-faint)]">{label}</span>
      <span className="text-sm text-[var(--color-text-primary)] break-all">{value}</span>
    </div>
  )
}

interface AuditLogDetailDrawerProps {
  open: boolean
  logId: string | null
  onClose: () => void
}

export default function AuditLogDetailDrawer({ open, logId, onClose }: AuditLogDetailDrawerProps) {
  const [metadataExpanded, setMetadataExpanded] = useState(true)

  const { data: log, isLoading, isError } = useQuery({
    queryKey: ['audit-logs', 'detail', logId],
    queryFn: () => auditLogsService.get(logId!),
    enabled: open && !!logId,
  })

  const Icon = log ? getModuleIcon(log.module) : Clock
  const metadata = log?.metadata ?? log?.details ?? null
  const hasMetadata = metadata && Object.keys(metadata).length > 0

  return (
    <Modal open={open} onClose={onClose} title={log ? formatActionLabel(log.action) : 'Audit log details'}>
      <div className="flex flex-col gap-5 max-h-[75vh] overflow-y-auto pr-1">
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : isError || !log ? (
          <ErrorBanner message="Couldn't load this audit log." />
        ) : (
          <>
            <div className="flex items-center gap-3 flex-wrap">
              <span className="flex items-center justify-center h-9 w-9 rounded-lg bg-[var(--color-surface-hover)]">
                <Icon size={16} className="text-[var(--color-text-muted)]" />
              </span>
              <div className="min-w-0">
                <p className="text-sm text-[var(--color-text-primary)]">
                  {log.summary ?? formatActionLabel(log.action)}
                </p>
                <p className="text-xs text-[var(--color-text-faint)]">
                  {getModuleLabel(log.module)} · {new Date(log.created_at).toLocaleString()}
                </p>
              </div>
              <Badge tone={getStatusTone(log.status)} className="ml-auto">
                {log.status ?? 'info'}
              </Badge>
            </div>

            {log.error_message && (
              <ErrorBanner message={log.error_message} />
            )}

            <div className="grid grid-cols-2 gap-4">
              <Field label="Action" value={<span className="font-mono">{log.action}</span>} />
              <Field label="Module" value={getModuleLabel(log.module)} />
              <Field label="Resource type" value={log.resource_type} />
              <Field
                label="Resource ID"
                value={log.resource_id && <span className="font-mono break-all">{log.resource_id}</span>}
              />
              <Field label="Actor" value={log.actor_type} />
              <Field label="Source" value={log.source} />
              <Field label="Duration" value={log.duration_ms != null ? `${log.duration_ms}ms` : null} />
              <Field label="Log ID" value={<span className="font-mono text-xs">{log.id}</span>} />
            </div>

            {hasMetadata && (
              <div>
                <button
                  type="button"
                  onClick={() => setMetadataExpanded((v) => !v)}
                  className="flex items-center gap-1.5 text-sm font-medium text-[var(--color-text-primary)] mb-2"
                >
                  {metadataExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  Metadata
                </button>
                {metadataExpanded && (
                  <pre className="text-[11px] leading-relaxed text-[var(--color-text-muted)] bg-[var(--color-surface)] border border-[var(--color-border)] rounded-md p-3 overflow-x-auto whitespace-pre-wrap break-all">
                    {JSON.stringify(metadata, null, 2)}
                  </pre>
                )}
              </div>
            )}

            {typeof metadata?.commit_url === 'string' || typeof metadata?.event_link === 'string' || typeof metadata?.issue_url === 'string' ? (
              <a
                href={
                  (metadata?.commit_url as string) ||
                  (metadata?.event_link as string) ||
                  (metadata?.issue_url as string)
                }
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 text-xs text-[var(--color-signal)] hover:underline w-fit"
              >
                View related resource <ExternalLink size={11} />
              </a>
            ) : null}
          </>
        )}
      </div>
    </Modal>
  )
}
