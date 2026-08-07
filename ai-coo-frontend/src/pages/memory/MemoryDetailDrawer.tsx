import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle,
  Archive,
  ChevronDown,
  ChevronRight,
  Pencil,
  Pin,
  RotateCcw,
  Star,
  Trash2,
} from 'lucide-react'
import { memoryService, type MemoryEntry } from '@/services/memory'
import Modal from '@/components/ui/Modal'
import Badge from '@/components/ui/Badge'
import Skeleton from '@/components/ui/Skeleton'
import { Button } from '@/components/ui/Button'
import { getCategoryIcon, getCategoryLabel, getImportanceTone } from '@/lib/memoryDisplay'

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

interface MemoryDetailDrawerProps {
  open: boolean
  memoryId: string | null
  orgId: string
  onClose: () => void
  onEdit: (memory: MemoryEntry) => void
}

export default function MemoryDetailDrawer({ open, memoryId, orgId, onClose, onEdit }: MemoryDetailDrawerProps) {
  const [metadataExpanded, setMetadataExpanded] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const queryClient = useQueryClient()

  const { data: memory, isLoading, isError } = useQuery({
    queryKey: ['memory', 'detail', memoryId],
    queryFn: () => memoryService.get(memoryId!, orgId),
    enabled: open && !!memoryId,
  })

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['memory'] })
  }

  const pinMutation = useMutation({
    mutationFn: () => (memory?.pinned ? memoryService.unpin(memory.id, orgId) : memoryService.pin(memory!.id, orgId)),
    onSuccess: invalidate,
  })

  const favoriteMutation = useMutation({
    mutationFn: () =>
      memory?.favorited ? memoryService.unfavorite(memory.id, orgId) : memoryService.favorite(memory!.id, orgId),
    onSuccess: invalidate,
  })

  const archiveMutation = useMutation({
    mutationFn: () => memoryService.archive(memory!.id, orgId),
    onSuccess: () => {
      invalidate()
      onClose()
    },
  })

  const restoreMutation = useMutation({
    mutationFn: () => memoryService.restore(memory!.id, orgId),
    onSuccess: invalidate,
  })

  const deleteMutation = useMutation({
    mutationFn: () => memoryService.remove(memory!.id, orgId),
    onSuccess: () => {
      invalidate()
      onClose()
    },
  })

  const Icon = memory ? getCategoryIcon(memory.category) : Pin
  const hasMetadata = memory?.metadata && Object.keys(memory.metadata).length > 0

  return (
    <Modal open={open} onClose={onClose} title={memory?.title ?? 'Memory details'}>
      <div className="flex flex-col gap-5 max-h-[75vh] overflow-y-auto pr-1">
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : isError || !memory ? (
          <ErrorBanner message="Couldn't load this memory." />
        ) : (
          <>
            <div className="flex items-center gap-3 flex-wrap">
              <span className="flex items-center justify-center h-9 w-9 rounded-lg bg-[var(--color-surface-hover)]">
                <Icon size={16} className="text-[var(--color-text-muted)]" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-xs text-[var(--color-text-faint)]">
                  {getCategoryLabel(memory.category)} · {new Date(memory.created_at).toLocaleString()}
                </p>
              </div>
              <Badge tone={getImportanceTone(memory.importance)}>{memory.importance ?? 'medium'}</Badge>
              {memory.status === 'archived' && <Badge tone="neutral">archived</Badge>}
            </div>

            <p className="text-sm text-[var(--color-text-primary)] whitespace-pre-wrap">{memory.content}</p>

            {memory.tags && memory.tags.length > 0 && (
              <div className="flex items-center gap-1.5 flex-wrap">
                {memory.tags.map((t) => (
                  <span key={t} className="text-xs text-[var(--color-text-muted)] bg-[var(--color-surface-hover)] rounded px-2 py-1">
                    {t}
                  </span>
                ))}
              </div>
            )}

            <div className="flex items-center gap-2 flex-wrap">
              <Button
                variant={memory.pinned ? 'primary' : 'secondary'}
                loading={pinMutation.isPending}
                onClick={() => pinMutation.mutate()}
              >
                <Pin size={13} fill={memory.pinned ? 'currentColor' : 'none'} />
                {memory.pinned ? 'Pinned' : 'Pin'}
              </Button>
              <Button
                variant={memory.favorited ? 'primary' : 'secondary'}
                loading={favoriteMutation.isPending}
                onClick={() => favoriteMutation.mutate()}
              >
                <Star size={13} fill={memory.favorited ? 'currentColor' : 'none'} />
                {memory.favorited ? 'Favorited' : 'Favorite'}
              </Button>
              <Button variant="secondary" onClick={() => onEdit(memory)}>
                <Pencil size={13} />
                Edit
              </Button>
              {memory.status === 'archived' ? (
                <Button variant="secondary" loading={restoreMutation.isPending} onClick={() => restoreMutation.mutate()}>
                  <RotateCcw size={13} />
                  Restore
                </Button>
              ) : (
                <Button variant="secondary" loading={archiveMutation.isPending} onClick={() => archiveMutation.mutate()}>
                  <Archive size={13} />
                  Archive
                </Button>
              )}
              <Button
                variant={confirmingDelete ? 'primary' : 'ghost'}
                onBlur={() => setConfirmingDelete(false)}
                loading={deleteMutation.isPending}
                className={confirmingDelete ? '!bg-[var(--color-alert)] !text-white' : ''}
                onClick={() => (confirmingDelete ? deleteMutation.mutate() : setConfirmingDelete(true))}
              >
                <Trash2 size={13} />
                {confirmingDelete ? 'Confirm?' : 'Delete'}
              </Button>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Source" value={memory.source} />
              <Field label="Access count" value={memory.access_count} />
              <Field
                label="Last accessed"
                value={memory.last_accessed_at ? new Date(memory.last_accessed_at).toLocaleString() : null}
              />
              <Field label="Updated" value={memory.updated_at ? new Date(memory.updated_at).toLocaleString() : null} />
              <Field label="Memory ID" value={<span className="font-mono text-xs">{memory.id}</span>} />
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
                    {JSON.stringify(memory.metadata, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </Modal>
  )
}
