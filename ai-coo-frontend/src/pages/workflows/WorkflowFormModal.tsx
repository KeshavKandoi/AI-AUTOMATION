import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Plus, Trash2 } from 'lucide-react'
import {
  workflowService,
  ALL_TRIGGER_TYPES,
  LIVE_TRIGGER_TYPES,
  ACTION_OPTIONS,
  ISSUE_CREATED_FIELDS,
  type ActionName,
  type TriggerType,
  type Workflow,
  type WorkflowStatus,
} from '@/services/workflows'
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

interface ConditionRow {
  field: string
  value: string
}

function conditionsToRows(conditions: Record<string, string>): ConditionRow[] {
  return Object.entries(conditions ?? {}).map(([field, value]) => ({ field, value }))
}

function rowsToConditions(rows: ConditionRow[]): Record<string, string> {
  const out: Record<string, string> = {}
  for (const row of rows) {
    if (row.field.trim() && row.value.trim()) {
      out[row.field.trim()] = row.value.trim()
    }
  }
  return out
}

interface WorkflowFormModalProps {
  open: boolean
  orgId: string
  workflow: Workflow | null
  onClose: () => void
  onSuccess: () => void
}

export default function WorkflowFormModal({ open, orgId, workflow, onClose, onSuccess }: WorkflowFormModalProps) {
  const isEdit = !!workflow
  const queryClient = useQueryClient()

  const [name, setName] = useState('')
  const [triggerType, setTriggerType] = useState<TriggerType>('issue_created')
  const [conditionRows, setConditionRows] = useState<ConditionRow[]>([])
  const [selectedActions, setSelectedActions] = useState<ActionName[]>([])
  const [status, setStatus] = useState<WorkflowStatus>('active')

  useEffect(() => {
    if (workflow) {
      setName(workflow.name)
      setTriggerType(workflow.trigger_type)
      setConditionRows(conditionsToRows(workflow.conditions))
      setSelectedActions(workflow.actions)
      setStatus(workflow.status)
    } else {
      setName('')
      setTriggerType('issue_created')
      setConditionRows([])
      setSelectedActions([])
      setStatus('active')
    }
  }, [workflow, open])

  const isLiveTrigger = (t: TriggerType) => LIVE_TRIGGER_TYPES.includes(t)

  const toggleAction = (action: ActionName) => {
    setSelectedActions((prev) =>
      prev.includes(action) ? prev.filter((a) => a !== action) : [...prev, action]
    )
  }

  const addConditionRow = () => {
    setConditionRows((prev) => [...prev, { field: ISSUE_CREATED_FIELDS[0], value: '' }])
  }

  const updateConditionRow = (index: number, patch: Partial<ConditionRow>) => {
    setConditionRows((prev) => prev.map((row, i) => (i === index ? { ...row, ...patch } : row)))
  }

  const removeConditionRow = (index: number) => {
    setConditionRows((prev) => prev.filter((_, i) => i !== index))
  }

  const createMutation = useMutation({
    mutationFn: () =>
      workflowService.createWorkflow({
        organization_id: orgId,
        name,
        trigger_type: triggerType,
        conditions: rowsToConditions(conditionRows),
        actions: selectedActions,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows', 'list'] })
      onSuccess()
    },
  })

  const updateMutation = useMutation({
    mutationFn: () =>
      workflowService.updateWorkflow(workflow!.id, orgId, {
        name,
        conditions: rowsToConditions(conditionRows),
        actions: selectedActions,
        status,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows', 'list'] })
      onSuccess()
    },
  })

  const mutation = isEdit ? updateMutation : createMutation

  const canSubmit = useMemo(
    () => name.trim().length > 0 && selectedActions.length > 0 && (isEdit || isLiveTrigger(triggerType)),
    [name, selectedActions, triggerType, isEdit]
  )

  return (
    <Modal open={open} onClose={onClose} title={isEdit ? 'Edit workflow' : 'New workflow'}>
      <div className="flex flex-col gap-4 max-h-[70vh] overflow-y-auto pr-1">
        <Input label="Name" placeholder="e.g. High priority issue fan-out" value={name} onChange={(e) => setName(e.target.value)} />

        <div className="flex flex-col gap-1.5">
          <label className={labelClass()}>Trigger</label>
          <select
            value={triggerType}
            onChange={(e) => setTriggerType(e.target.value as TriggerType)}
            disabled={isEdit}
            className={selectClass()}
          >
            {ALL_TRIGGER_TYPES.map((t) => (
              <option key={t.value} value={t.value} disabled={!isLiveTrigger(t.value)}>
                {t.label}
                {!isLiveTrigger(t.value) ? ' (coming soon)' : ''}
              </option>
            ))}
          </select>
          {!isLiveTrigger(triggerType) && (
            <p className="text-xs text-[var(--color-amber)]">
              This trigger isn't wired up to fire workflows yet — choose "Issue created" for now.
            </p>
          )}
          {isEdit && (
            <p className="text-xs text-[var(--color-text-faint)]">
              Trigger can't be changed after creation — delete and recreate the workflow if this needs to change.
            </p>
          )}
        </div>

        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <label className={labelClass()}>Conditions</label>
            <button
              type="button"
              onClick={addConditionRow}
              className="text-xs text-[var(--color-signal)] hover:underline flex items-center gap-1"
            >
              <Plus size={12} />
              Add condition
            </button>
          </div>
          {conditionRows.length === 0 ? (
            <p className="text-xs text-[var(--color-text-faint)]">No conditions — this workflow runs on every matching event.</p>
          ) : (
            <div className="flex flex-col gap-2">
              {conditionRows.map((row, i) => (
                <div key={i} className="flex items-center gap-2">
                  <select
                    value={row.field}
                    onChange={(e) => updateConditionRow(i, { field: e.target.value })}
                    className={selectClass()}
                  >
                    {ISSUE_CREATED_FIELDS.map((f) => (
                      <option key={f} value={f}>{f}</option>
                    ))}
                  </select>
                  <span className="text-xs text-[var(--color-text-faint)] shrink-0">=</span>
                  <Input
                    placeholder="value"
                    value={row.value}
                    onChange={(e) => updateConditionRow(i, { value: e.target.value })}
                  />
                  <button
                    type="button"
                    onClick={() => removeConditionRow(i)}
                    className="text-[var(--color-text-faint)] hover:text-[var(--color-alert)] transition-colors p-2 shrink-0"
                    title="Remove condition"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-1.5">
          <label className={labelClass()}>Actions</label>
          <div className="flex flex-col gap-2 border border-[var(--color-border)] rounded-lg p-3">
            {ACTION_OPTIONS.map((opt) => (
              <label key={opt.value} className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedActions.includes(opt.value)}
                  onChange={() => toggleAction(opt.value)}
                  className="accent-[var(--color-signal)] mt-0.5"
                />
                <div>
                  <p className="text-sm text-[var(--color-text-primary)]">{opt.label}</p>
                  <p className="text-xs text-[var(--color-text-faint)]">{opt.description}</p>
                </div>
              </label>
            ))}
          </div>
          {selectedActions.length === 0 && (
            <p className="text-xs text-[var(--color-text-faint)]">Select at least one action.</p>
          )}
        </div>

        {isEdit && (
          <div className="flex flex-col gap-1.5">
            <label className={labelClass()}>Status</label>
            <select value={status} onChange={(e) => setStatus(e.target.value as WorkflowStatus)} className={selectClass()}>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
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
          {isEdit ? 'Save changes' : 'Create workflow'}
        </Button>
      </div>
    </Modal>
  )
}
