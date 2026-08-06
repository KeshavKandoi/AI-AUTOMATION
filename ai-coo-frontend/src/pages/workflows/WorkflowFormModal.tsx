import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Plus, Trash2 } from 'lucide-react'
import {
  workflowService,
  ALL_TRIGGER_TYPES,
  ACTION_OPTIONS,
  TRIGGER_FIELDS,
  isConditionGroup,
  conditionsToRuleList,
  type ActionName,
  type ConditionOp,
  type ConditionLogic,
  type Conditions,
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

interface ConditionRowUI {
  field: string
  op: ConditionOp
  value: string
}

function conditionsToRows(conditions: Conditions): ConditionRowUI[] {
  return conditionsToRuleList(conditions).map((r) => ({
    field: r.field,
    op: r.op,
    value: Array.isArray(r.value) ? r.value.join(', ') : r.value,
  }))
}

function initialLogic(conditions: Conditions | null | undefined): ConditionLogic {
  if (conditions && isConditionGroup(conditions)) return conditions.logic
  return 'AND'
}

function rowsToConditions(rows: ConditionRowUI[], logic: ConditionLogic): Conditions {
  const rules = rows
    .filter((r) => r.field.trim() && r.value.trim())
    .map((r) => ({
      field: r.field.trim(),
      op: r.op,
      value:
        r.op === 'in'
          ? r.value.split(',').map((v) => v.trim()).filter(Boolean)
          : r.value.trim(),
    }))
  if (rules.length === 0) return {}
  return { logic, rules }
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
  const [conditionRows, setConditionRows] = useState<ConditionRowUI[]>([])
  const [conditionLogic, setConditionLogic] = useState<ConditionLogic>('AND')
  const [selectedActions, setSelectedActions] = useState<ActionName[]>([])
  const [status, setStatus] = useState<WorkflowStatus>('active')

  useEffect(() => {
    if (workflow) {
      setName(workflow.name)
      setTriggerType(workflow.trigger_type)
      setConditionRows(conditionsToRows(workflow.conditions))
      setConditionLogic(initialLogic(workflow.conditions))
      setSelectedActions(workflow.actions)
      setStatus(workflow.status)
    } else {
      setName('')
      setTriggerType('issue_created')
      setConditionRows([])
      setConditionLogic('AND')
      setSelectedActions([])
      setStatus('active')
    }
  }, [workflow, open])

  const fieldsForTrigger = TRIGGER_FIELDS[triggerType]

  const toggleAction = (action: ActionName) => {
    setSelectedActions((prev) =>
      prev.includes(action) ? prev.filter((a) => a !== action) : [...prev, action]
    )
  }

  const handleTriggerChange = (next: TriggerType) => {
    setTriggerType(next)
    // Condition fields are trigger-specific — stale rows from a different
    // trigger's field set would silently never match, so clear them.
    setConditionRows([])
  }

  const addConditionRow = () => {
    setConditionRows((prev) => [...prev, { field: fieldsForTrigger[0]?.field ?? '', op: 'eq', value: '' }])
  }

  const updateConditionRow = (index: number, patch: Partial<ConditionRowUI>) => {
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
        conditions: rowsToConditions(conditionRows, conditionLogic),
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
        conditions: rowsToConditions(conditionRows, conditionLogic),
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
    () => name.trim().length > 0 && selectedActions.length > 0,
    [name, selectedActions]
  )

  return (
    <Modal open={open} onClose={onClose} title={isEdit ? 'Edit workflow' : 'New workflow'}>
      <div className="flex flex-col gap-4 max-h-[70vh] overflow-y-auto pr-1">
        <Input label="Name" placeholder="e.g. High priority issue fan-out" value={name} onChange={(e) => setName(e.target.value)} />

        <div className="flex flex-col gap-1.5">
          <label className={labelClass()}>Trigger</label>
          <select
            value={triggerType}
            onChange={(e) => handleTriggerChange(e.target.value as TriggerType)}
            disabled={isEdit}
            className={selectClass()}
          >
            {ALL_TRIGGER_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-[var(--color-text-faint)]">
            {ALL_TRIGGER_TYPES.find((t) => t.value === triggerType)?.description}
          </p>
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
              {conditionRows.length > 1 && (
                <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
                  <span>Match</span>
                  <div className="flex rounded-md border border-[var(--color-border)] overflow-hidden">
                    {(['AND', 'OR'] as ConditionLogic[]).map((logic) => (
                      <button
                        key={logic}
                        type="button"
                        onClick={() => setConditionLogic(logic)}
                        className={
                          conditionLogic === logic
                            ? 'px-2.5 py-1 bg-[var(--color-signal)] text-white'
                            : 'px-2.5 py-1 text-[var(--color-text-muted)] hover:bg-[var(--color-surface)]'
                        }
                      >
                        {logic}
                      </button>
                    ))}
                  </div>
                  <span>of the rules below</span>
                </div>
              )}

              {conditionRows.map((row, i) => {
                const fieldMeta = fieldsForTrigger.find((f) => f.field === row.field)
                return (
                  <div key={i} className="flex items-center gap-2">
                    <select
                      value={row.field}
                      onChange={(e) => updateConditionRow(i, { field: e.target.value })}
                      className={selectClass()}
                    >
                      {fieldsForTrigger.map((f) => (
                        <option key={f.field} value={f.field}>{f.label}</option>
                      ))}
                    </select>
                    <select
                      value={row.op}
                      onChange={(e) => updateConditionRow(i, { op: e.target.value as ConditionOp })}
                      className={`${selectClass()} max-w-[90px] shrink-0`}
                    >
                      <option value="eq">is</option>
                      <option value="in">in</option>
                    </select>
                    <Input
                      placeholder={row.op === 'in' ? `${fieldMeta?.example ?? 'value'}, ...` : fieldMeta?.example ?? 'value'}
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
                )
              })}
              {conditionRows.some((r) => r.op === 'in') && (
                <p className="text-xs text-[var(--color-text-faint)]">Separate multiple values with commas for "in" conditions.</p>
              )}
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
