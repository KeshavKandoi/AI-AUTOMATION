import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertCircle } from 'lucide-react'
import { memoryService, type MemoryEntry, type MemoryImportance } from '@/services/memory'
import { ALL_CATEGORIES, getCategoryLabel } from '@/lib/memoryDisplay'
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
  return 'w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)]'
}

function labelClass() {
  return 'text-sm font-medium text-[var(--color-text-muted)]'
}

interface MemoryFormModalProps {
  open: boolean
  orgId: string
  memory: MemoryEntry | null
  onClose: () => void
  onSuccess: () => void
}

export default function MemoryFormModal({ open, orgId, memory, onClose, onSuccess }: MemoryFormModalProps) {
  const isEdit = !!memory
  const queryClient = useQueryClient()

  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [category, setCategory] = useState('custom')
  const [importance, setImportance] = useState<MemoryImportance>('medium')
  const [tagsInput, setTagsInput] = useState('')

  useEffect(() => {
    if (memory) {
      setTitle(memory.title ?? '')
      setContent(memory.content)
      setCategory(memory.category ?? 'custom')
      setImportance((memory.importance as MemoryImportance) ?? 'medium')
      setTagsInput((memory.tags ?? []).join(', '))
    } else {
      setTitle('')
      setContent('')
      setCategory('custom')
      setImportance('medium')
      setTagsInput('')
    }
  }, [memory, open])

  const parsedTags = tagsInput.split(',').map((t) => t.trim()).filter(Boolean)

  const createMutation = useMutation({
    mutationFn: () =>
      memoryService.create({
        organization_id: orgId,
        title,
        content,
        category,
        importance,
        tags: parsedTags,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memory'] })
      onSuccess()
    },
  })

  const updateMutation = useMutation({
    mutationFn: () =>
      memoryService.update(memory!.id, orgId, {
        title,
        content,
        category,
        importance,
        tags: parsedTags,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memory'] })
      onSuccess()
    },
  })

  const mutation = isEdit ? updateMutation : createMutation
  const canSubmit = title.trim() && content.trim()

  return (
    <Modal open={open} onClose={onClose} title={isEdit ? 'Edit memory' : 'New memory'}>
      <div className="flex flex-col gap-4 max-h-[70vh] overflow-y-auto pr-1">
        <Input label="Title" placeholder="e.g. Preferred deploy window" value={title} onChange={(e) => setTitle(e.target.value)} />

        <div className="flex flex-col gap-1.5">
          <label className={labelClass()}>Content</label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={5}
            placeholder="What should AI COO remember?"
            className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-faint)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)] resize-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <label className={labelClass()}>Category</label>
            <select value={category} onChange={(e) => setCategory(e.target.value)} className={selectClass()}>
              {ALL_CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {getCategoryLabel(c)}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1.5">
            <label className={labelClass()}>Importance</label>
            <select value={importance} onChange={(e) => setImportance(e.target.value as MemoryImportance)} className={selectClass()}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
        </div>

        <Input
          label="Tags (comma-separated)"
          placeholder="e.g. deploy, ops"
          value={tagsInput}
          onChange={(e) => setTagsInput(e.target.value)}
        />

        {mutation.isError && (
          <ErrorBanner
            message={
              (mutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
              'Something went wrong. Please check the fields and try again.'
            }
          />
        )}

        <Button className="w-full" disabled={!canSubmit} loading={mutation.isPending} onClick={() => mutation.mutate()}>
          {isEdit ? 'Save changes' : 'Create memory'}
        </Button>
      </div>
    </Modal>
  )
}
