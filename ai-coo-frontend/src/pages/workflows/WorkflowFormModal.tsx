import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle,
  Calendar,
  CalendarClock,
  CheckSquare,
  ChevronDown,
  FileText,
  FileWarning,
  GitCommit,
  GitPullRequest,
  Infinity as InfinityIcon,
  Info,
  Mail,
  MessageSquare,
  Plus,
  Sparkles,
  Trash2,
  X,
  Zap,
} from 'lucide-react'
import {
  workflowService,
  ALL_TRIGGER_TYPES,
  ACTION_OPTIONS,
  TRIGGER_FIELDS,
  LIFETIME_MODE_OPTIONS,
  isConditionGroup,
  conditionsToRuleList,
  type ActionName,
  type ConditionOp,
  type ConditionLogic,
  type Conditions,
  type LifetimeMode,
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

function HelpHint({ text }: { text: string }) {
  return (
    <span title={text} className="inline-flex text-[var(--color-text-faint)] cursor-help">
      <Info size={12} />
    </span>
  )
}

// --- Trigger presentation -------------------------------------------------

const TRIGGER_ICON: Record<TriggerType, typeof FileWarning> = {
  issue_created: FileWarning,
  push: GitCommit,
  pull_request_opened: GitPullRequest,
}

const TRIGGER_PHRASE: Record<TriggerType, string> = {
  issue_created: 'an issue is created',
  push: 'code is pushed',
  pull_request_opened: 'a pull request is opened',
}

// --- Action presentation ---------------------------------------------------

const ACTION_ICON: Record<ActionName, typeof Mail> = {
  create_task: CheckSquare,
  send_email: Mail,
  notify_discord: MessageSquare,
  create_calendar_event: Calendar,
  save_audit_log: FileText,
}

// --- Lifetime presentation --------------------------------------------

const LIFETIME_ICON: Record<LifetimeMode, typeof InfinityIcon> = {
  continuous: InfinityIcon,
  run_once: Zap,
  until_date: CalendarClock,
}

function toDatetimeLocalValue(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function minDatetimeLocalValue(): string {
  return toDatetimeLocalValue(new Date(Date.now() + 60 * 1000).toISOString())
}

function datetimeLocalToISO(value: string): string | null {
  if (!value) return null
  const d = new Date(value)
  return isNaN(d.getTime()) ? null : d.toISOString()
}

function isFutureLocal(value: string): boolean {
  if (!value) return false
  const d = new Date(value)
  return !isNaN(d.getTime()) && d.getTime() > Date.now()
}

function lifetimeClause(mode: LifetimeMode, expiresAtLocal: string): string {
  if (mode === 'run_once') {
    return ' This workflow will run once and then mark itself Completed.'
  }
  if (mode === 'until_date' && expiresAtLocal) {
    const d = new Date(expiresAtLocal)
    if (!isNaN(d.getTime())) {
      return ` This workflow will stop running after ${d.toLocaleString()} and mark itself Expired.`
    }
  }
  return ''
}

// --- Field UI config ---------------------------------------------------
// Maps each backend-supported condition field (from TRIGGER_FIELDS) to the
// friendliest input control for its data shape. Every field here must exist
// in TRIGGER_FIELDS — we never invent a filter the backend can't evaluate.
// NOTE: `priority` options and branch suggestions are inferred from the one
// example context we've seen; confirm against the real backend enum/values
// and adjust if they differ.
type FieldControl = 'select' | 'multiselect' | 'text' | 'number' | 'boolean' | 'autocomplete'

interface FieldUIConfig {
  control: FieldControl
  options?: string[]
}

const FIELD_UI: Record<TriggerType, Record<string, FieldUIConfig>> = {
  issue_created: {
    priority: { control: 'select', options: ['low', 'medium', 'high', 'critical'] },
    labels: { control: 'multiselect' },
    repo: { control: 'text' },
    issue_number: { control: 'number' },
    title: { control: 'text' },
    author: { control: 'text' },
    assignee: { control: 'text' },
  },
  push: {
    repo: { control: 'text' },
    branch: { control: 'autocomplete', options: ['main', 'master', 'develop', 'staging'] },
    author: { control: 'text' },
    commit_message: { control: 'text' },
    commit_sha: { control: 'text' },
    commit_count: { control: 'number' },
  },
  pull_request_opened: {
    repo: { control: 'text' },
    title: { control: 'text' },
    author: { control: 'text' },
    source_branch: { control: 'autocomplete', options: ['main', 'master', 'develop'] },
    target_branch: { control: 'autocomplete', options: ['main', 'master', 'develop'] },
    draft: { control: 'boolean' },
    labels: { control: 'multiselect' },
  },
}

function defaultOpFor(control: FieldControl): ConditionOp {
  return control === 'multiselect' ? 'in' : 'eq'
}

// --- Row state ---------------------------------------------------------

interface ConditionRowUI {
  field: string
  op: ConditionOp
  value: string | string[]
}

function conditionsToRows(conditions: Conditions): ConditionRowUI[] {
  return conditionsToRuleList(conditions).map((r) => ({ field: r.field, op: r.op, value: r.value }))
}

function initialLogic(conditions: Conditions | null | undefined): ConditionLogic {
  if (conditions && isConditionGroup(conditions)) return conditions.logic
  return 'AND'
}

// Existing OR-logic workflows carry semantics that Simple mode can't safely
// represent (it only ever writes AND), so open those in Advanced mode rather
// than risk silently flattening OR into AND on save.
function shouldStartAdvanced(conditions: Conditions | null | undefined): boolean {
  if (!conditions) return false
  const rules = conditionsToRuleList(conditions)
  return isConditionGroup(conditions) && conditions.logic === 'OR' && rules.length > 1
}

function rowsToConditions(rows: ConditionRowUI[], logic: ConditionLogic): Conditions {
  const rules = rows
    .filter((r) => (Array.isArray(r.value) ? r.value.length > 0 : r.value.trim().length > 0))
    .map((r) => ({ field: r.field, op: r.op, value: r.value }))
  if (rules.length === 0) return {}
  return { logic, rules }
}

function fieldLabel(triggerType: TriggerType, field: string): string {
  return TRIGGER_FIELDS[triggerType].find((f) => f.field === field)?.label ?? field
}

function valueDisplay(value: string | string[]): string {
  return Array.isArray(value) ? value.join(', ') : value
}

function ruleToPhrase(triggerType: TriggerType, row: ConditionRowUI): string {
  const label = fieldLabel(triggerType, row.field).toLowerCase()
  if (row.field === 'draft') {
    return row.value === 'true' ? 'it is a draft' : 'it is not a draft'
  }
  if (row.op === 'in') {
    return `${label} is one of ${valueDisplay(row.value)}`
  }
  return `${label} is "${valueDisplay(row.value)}"`
}

function buildSummary(
  triggerType: TriggerType,
  rows: ConditionRowUI[],
  logic: ConditionLogic,
  actions: ActionName[]
): string {
  const validRows = rows.filter((r) => (Array.isArray(r.value) ? r.value.length > 0 : r.value.trim().length > 0))
  let clause = ''
  if (validRows.length > 0) {
    const parts = validRows.map((r) => ruleToPhrase(triggerType, r))
    clause = ` and ${logic === 'OR' ? 'at least one of these is true' : 'all of these are true'}: ${parts.join(
      logic === 'OR' ? ', or ' : ', and '
    )}`
  }
  if (actions.length === 0) {
    return `When ${TRIGGER_PHRASE[triggerType]}${clause}, choose an action below to complete this workflow.`
  }
  const actionPhrase = actions.map((a) => ACTION_OPTIONS.find((o) => o.value === a)?.label.toLowerCase()).join(', and ')
  const sentence = `When ${TRIGGER_PHRASE[triggerType]}${clause}, we'll ${actionPhrase}.`
  return sentence.charAt(0).toUpperCase() + sentence.slice(1)
}

// --- Field input renderer ------------------------------------------------

function MultiSelectTagInput({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  const [draft, setDraft] = useState('')
  const commit = () => {
    const v = draft.trim()
    if (v && !value.includes(v)) onChange([...value, v])
    setDraft('')
  }
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex flex-wrap gap-1.5">
        {value.map((t) => (
          <span key={t} className="flex items-center gap-1 rounded-full bg-[var(--color-surface)] border border-[var(--color-border)] px-2.5 py-1 text-xs text-[var(--color-text-primary)]">
            {t}
            <button type="button" onClick={() => onChange(value.filter((x) => x !== t))}>
              <X size={11} className="text-[var(--color-text-faint)] hover:text-[var(--color-alert)]" />
            </button>
          </span>
        ))}
      </div>
      <Input
        placeholder="Type a value and press Enter"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault()
            commit()
          }
        }}
      />
    </div>
  )
}

function FieldValueInput({
  config,
  value,
  onChange,
}: {
  config: FieldUIConfig
  value: string | string[]
  onChange: (v: string | string[]) => void
}) {
  if (config.control === 'select') {
    return (
      <select value={typeof value === 'string' ? value : ''} onChange={(e) => onChange(e.target.value)} className={selectClass()}>
        <option value="" disabled>Choose a value…</option>
        {config.options?.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    )
  }

  if (config.control === 'boolean') {
    const current = typeof value === 'string' ? value : ''
    return (
      <div className="flex rounded-md border border-[var(--color-border)] overflow-hidden text-xs">
        {[
          { v: '', label: 'Any' },
          { v: 'true', label: 'Yes' },
          { v: 'false', label: 'No' },
        ].map((opt) => (
          <button
            key={opt.label}
            type="button"
            onClick={() => onChange(opt.v)}
            className={
              current === opt.v
                ? 'px-3 py-2 bg-[var(--color-signal)] text-white'
                : 'px-3 py-2 text-[var(--color-text-muted)] hover:bg-[var(--color-surface)]'
            }
          >
            {opt.label}
          </button>
        ))}
      </div>
    )
  }

  if (config.control === 'multiselect') {
    return <MultiSelectTagInput value={Array.isArray(value) ? value : []} onChange={onChange} />
  }

  if (config.control === 'autocomplete') {
    const listId = `list-${Math.random().toString(36).slice(2)}`
    return (
      <>
        <Input
          list={listId}
          placeholder="e.g. main"
          value={typeof value === 'string' ? value : ''}
          onChange={(e) => onChange(e.target.value)}
        />
        <datalist id={listId}>
          {config.options?.map((o) => <option key={o} value={o} />)}
        </datalist>
      </>
    )
  }

  if (config.control === 'number') {
    return (
      <Input
        type="number"
        placeholder="e.g. 1"
        value={typeof value === 'string' ? value : ''}
        onChange={(e) => onChange(e.target.value)}
      />
    )
  }

  return (
    <Input
      placeholder="Type a value"
      value={typeof value === 'string' ? value : ''}
      onChange={(e) => onChange(e.target.value)}
    />
  )
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
  const [advancedMode, setAdvancedMode] = useState(false)
  const [lifetimeMode, setLifetimeMode] = useState<LifetimeMode>('continuous')
  const [expiresAtLocal, setExpiresAtLocal] = useState('')

  useEffect(() => {
    if (workflow) {
      setName(workflow.name)
      setTriggerType(workflow.trigger_type)
      setConditionRows(conditionsToRows(workflow.conditions))
      setConditionLogic(initialLogic(workflow.conditions))
      setSelectedActions(workflow.actions)
      setStatus(workflow.status)
      setAdvancedMode(shouldStartAdvanced(workflow.conditions))
      setLifetimeMode(workflow.lifetime_mode)
      setExpiresAtLocal(toDatetimeLocalValue(workflow.expires_at))
    } else {
      setName('')
      setTriggerType('issue_created')
      setConditionRows([])
      setConditionLogic('AND')
      setSelectedActions([])
      setStatus('active')
      setAdvancedMode(false)
      setLifetimeMode('continuous')
      setExpiresAtLocal('')
    }
  }, [workflow, open])

  const fieldsForTrigger = TRIGGER_FIELDS[triggerType]
  const fieldUIForTrigger = FIELD_UI[triggerType]
  const usedFields = new Set(conditionRows.map((r) => r.field))
  const availableFields = fieldsForTrigger.filter((f) => !usedFields.has(f.field))

  const toggleAction = (action: ActionName) => {
    setSelectedActions((prev) => (prev.includes(action) ? prev.filter((a) => a !== action) : [...prev, action]))
  }

  const handleLifetimeChange = (mode: LifetimeMode) => {
    setLifetimeMode(mode)
    if (mode !== 'until_date') setExpiresAtLocal('')
  }

  const handleTriggerChange = (next: TriggerType) => {
    setTriggerType(next)
    // Filters are trigger-specific — stale rows from a different trigger's
    // field set would silently never match, so clear them.
    setConditionRows([])
  }

  const addSimpleFilter = (field: string) => {
    const control = fieldUIForTrigger[field]?.control ?? 'text'
    setConditionRows((prev) => [...prev, { field, op: defaultOpFor(control), value: control === 'multiselect' ? [] : '' }])
  }

  const addAdvancedRow = () => {
    const field = fieldsForTrigger[0]?.field ?? ''
    setConditionRows((prev) => [...prev, { field, op: 'eq', value: '' }])
  }

  const updateRowValue = (index: number, value: string | string[]) => {
    setConditionRows((prev) => prev.map((row, i) => (i === index ? { ...row, value } : row)))
  }

  const updateRowField = (index: number, field: string) => {
    setConditionRows((prev) => prev.map((row, i) => (i === index ? { ...row, field, value: '' } : row)))
  }

  const updateRowOp = (index: number, op: ConditionOp) => {
    setConditionRows((prev) => prev.map((row, i) => (i === index ? { ...row, op, value: op === 'in' ? [] : '' } : row)))
  }

  const removeRow = (index: number) => {
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
        lifetime_mode: lifetimeMode,
        expires_at: lifetimeMode === 'until_date' ? datetimeLocalToISO(expiresAtLocal) : null,
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
        lifetime_mode: lifetimeMode,
        expires_at: lifetimeMode === 'until_date' ? datetimeLocalToISO(expiresAtLocal) : null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows', 'list'] })
      onSuccess()
    },
  })

  const mutation = isEdit ? updateMutation : createMutation

  const canSubmit = useMemo(
    () =>
      name.trim().length > 0 &&
      selectedActions.length > 0 &&
      (lifetimeMode !== 'until_date' || isFutureLocal(expiresAtLocal)),
    [name, selectedActions, lifetimeMode, expiresAtLocal]
  )

  const summary = useMemo(
    () => buildSummary(triggerType, conditionRows, conditionLogic, selectedActions) + lifetimeClause(lifetimeMode, expiresAtLocal),
    [triggerType, conditionRows, conditionLogic, selectedActions, lifetimeMode, expiresAtLocal]
  )

  return (
    <Modal open={open} onClose={onClose} title={isEdit ? 'Edit workflow' : 'New workflow'}>
      <div className="flex flex-col gap-6 max-h-[70vh] overflow-y-auto pr-1">
        <Input label="Name" placeholder="e.g. High priority issue fan-out" value={name} onChange={(e) => setName(e.target.value)} />

        {/* When this happens... */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-1.5">
            <label className={labelClass()}>When this happens…</label>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {ALL_TRIGGER_TYPES.map((t) => {
              const Icon = TRIGGER_ICON[t.value]
              const selected = triggerType === t.value
              return (
                <button
                  key={t.value}
                  type="button"
                  disabled={isEdit}
                  onClick={() => handleTriggerChange(t.value)}
                  className={
                    (selected
                      ? 'border-[var(--color-signal)] bg-[var(--color-signal-dim)]'
                      : 'border-[var(--color-border)] hover:border-[var(--color-signal)]') +
                    ' flex flex-col items-start gap-1.5 rounded-lg border p-3 text-left transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
                  }
                >
                  <Icon size={16} className={selected ? 'text-[var(--color-signal)]' : 'text-[var(--color-text-muted)]'} />
                  <span className="text-sm font-medium text-[var(--color-text-primary)]">{t.label}</span>
                  <span className="text-xs text-[var(--color-text-faint)]">{t.description}</span>
                </button>
              )
            })}
          </div>
          {isEdit && (
            <p className="text-xs text-[var(--color-text-faint)]">
              The trigger can't be changed after creation — delete and recreate the workflow if this needs to change.
            </p>
          )}
        </div>

        {/* Only if... */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <label className={labelClass()}>Only if… <span className="font-normal text-[var(--color-text-faint)]">(optional)</span></label>
              <HelpHint text="Add filters to only run this workflow when specific details match. Leave empty to run every time." />
            </div>
            <button
              type="button"
              onClick={() => setAdvancedMode((v) => !v)}
              className="flex items-center gap-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-signal)]"
            >
              <Sparkles size={12} />
              {advancedMode ? 'Simple mode' : 'Advanced mode'}
            </button>
          </div>

          {conditionRows.length === 0 && (
            <p className="text-xs text-[var(--color-text-faint)] italic">
              Example: only if priority is "high" — otherwise this runs on every {ALL_TRIGGER_TYPES.find((t) => t.value === triggerType)?.label.toLowerCase()} event.
            </p>
          )}

          {!advancedMode ? (
            <>
              {/* Simple mode: pick from field chips, each rendered with its natural control */}
              {conditionRows.length > 0 && (
                <div className="flex flex-col gap-2">
                  {conditionRows.map((row, i) => {
                    const config = fieldUIForTrigger[row.field] ?? { control: 'text' as FieldControl }
                    return (
                      <div key={row.field}>
                        {i > 0 && <p className="text-[10px] uppercase tracking-wide text-[var(--color-text-faint)] mb-1">and</p>}
                        <div className="flex items-start gap-2 rounded-lg border border-[var(--color-border)] p-2.5">
                          <div className="flex-1 flex flex-col gap-1">
                            <span className="text-xs font-medium text-[var(--color-text-primary)]">
                              {fieldLabel(triggerType, row.field)}
                            </span>
                            <FieldValueInput config={config} value={row.value} onChange={(v) => updateRowValue(i, v)} />
                          </div>
                          <button
                            type="button"
                            onClick={() => removeRow(i)}
                            className="text-[var(--color-text-faint)] hover:text-[var(--color-alert)] transition-colors p-1.5 shrink-0"
                            title="Remove filter"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
              {availableFields.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {availableFields.map((f) => (
                    <button
                      key={f.field}
                      type="button"
                      onClick={() => addSimpleFilter(f.field)}
                      className="flex items-center gap-1 rounded-full border border-dashed border-[var(--color-border)] px-2.5 py-1 text-xs text-[var(--color-text-muted)] hover:border-[var(--color-signal)] hover:text-[var(--color-signal)] transition-colors"
                    >
                      <Plus size={11} />
                      {f.label}
                    </button>
                  ))}
                </div>
              )}
            </>
          ) : (
            <>
              {/* Advanced mode: AND/OR groups, explicit operator, any field */}
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
                  <span>of these rules</span>
                </div>
              )}
              {conditionRows.map((row, i) => {
                const fieldMeta = fieldsForTrigger.find((f) => f.field === row.field)
                return (
                  <div key={i} className="flex items-center gap-2">
                    <select value={row.field} onChange={(e) => updateRowField(i, e.target.value)} className={selectClass()}>
                      {fieldsForTrigger.map((f) => (
                        <option key={f.field} value={f.field}>{f.label}</option>
                      ))}
                    </select>
                    <select
                      value={row.op}
                      onChange={(e) => updateRowOp(i, e.target.value as ConditionOp)}
                      className={`${selectClass()} max-w-[90px] shrink-0`}
                    >
                      <option value="eq">is</option>
                      <option value="in">is one of</option>
                    </select>
                    {row.op === 'in' ? (
                      <Input
                        placeholder={`${fieldMeta?.example ?? 'value'}, …`}
                        value={Array.isArray(row.value) ? row.value.join(', ') : ''}
                        onChange={(e) => updateRowValue(i, e.target.value.split(',').map((v) => v.trim()).filter(Boolean))}
                      />
                    ) : (
                      <Input
                        placeholder={fieldMeta?.example ?? 'value'}
                        value={typeof row.value === 'string' ? row.value : ''}
                        onChange={(e) => updateRowValue(i, e.target.value)}
                      />
                    )}
                    <button
                      type="button"
                      onClick={() => removeRow(i)}
                      className="text-[var(--color-text-faint)] hover:text-[var(--color-alert)] transition-colors p-2 shrink-0"
                      title="Remove condition"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                )
              })}
              <button
                type="button"
                onClick={addAdvancedRow}
                className="self-start text-xs text-[var(--color-signal)] hover:underline flex items-center gap-1"
              >
                <Plus size={12} />
                Add rule
              </button>
              {conditionRows.some((r) => r.op === 'in') && (
                <p className="text-xs text-[var(--color-text-faint)]">Separate multiple values with commas for "is one of" rules.</p>
              )}
            </>
          )}
        </div>

        {/* Then do this... */}
        <div className="flex flex-col gap-2">
          <label className={labelClass()}>Then do this…</label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {ACTION_OPTIONS.map((opt) => {
              const Icon = ACTION_ICON[opt.value]
              const selected = selectedActions.includes(opt.value)
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => toggleAction(opt.value)}
                  className={
                    (selected
                      ? 'border-[var(--color-signal)] bg-[var(--color-signal-dim)]'
                      : 'border-[var(--color-border)] hover:border-[var(--color-signal)]') +
                    ' flex items-start gap-2.5 rounded-lg border p-3 text-left transition-colors'
                  }
                >
                  <Icon size={16} className={(selected ? 'text-[var(--color-signal)]' : 'text-[var(--color-text-muted)]') + ' mt-0.5 shrink-0'} />
                  <div>
                    <p className="text-sm font-medium text-[var(--color-text-primary)]">{opt.label}</p>
                    <p className="text-xs text-[var(--color-text-faint)]">{opt.description}</p>
                  </div>
                </button>
              )
            })}
          </div>
          {selectedActions.length === 0 && (
            <p className="text-xs text-[var(--color-text-faint)]">Pick at least one action.</p>
          )}
        </div>

        {/* Workflow lifetime */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-1.5">
            <label className={labelClass()}>Workflow lifetime</label>
            <HelpHint text="Choose whether this workflow keeps running, runs once and stops, or stops automatically after a date and time." />
          </div>
          <div className="flex flex-col gap-2">
            {LIFETIME_MODE_OPTIONS.map((opt) => {
              const Icon = LIFETIME_ICON[opt.value]
              const selected = lifetimeMode === opt.value
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => handleLifetimeChange(opt.value)}
                  className={
                    (selected
                      ? 'border-[var(--color-signal)] bg-[var(--color-signal-dim)]'
                      : 'border-[var(--color-border)] hover:border-[var(--color-signal)]') +
                    ' flex items-start gap-2.5 rounded-lg border p-3 text-left transition-colors'
                  }
                >
                  <Icon size={16} className={(selected ? 'text-[var(--color-signal)]' : 'text-[var(--color-text-muted)]') + ' mt-0.5 shrink-0'} />
                  <div>
                    <p className="text-sm font-medium text-[var(--color-text-primary)]">{opt.label}</p>
                    <p className="text-xs text-[var(--color-text-faint)]">{opt.description}</p>
                  </div>
                </button>
              )
            })}
          </div>
          {lifetimeMode === 'until_date' && (
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-[var(--color-text-muted)]">Stop running after</label>
              <Input
                type="datetime-local"
                min={minDatetimeLocalValue()}
                value={expiresAtLocal}
                onChange={(e) => setExpiresAtLocal(e.target.value)}
              />
              {expiresAtLocal && !isFutureLocal(expiresAtLocal) && (
                <p className="text-xs text-[var(--color-alert)]">Pick a date and time in the future.</p>
              )}
            </div>
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

        {/* Live summary */}
        <div className="flex items-start gap-2 rounded-lg border border-[var(--color-signal-dim)] bg-[var(--color-signal-dim)] px-3 py-2.5">
          <ChevronDown size={14} className="text-[var(--color-signal)] shrink-0 mt-0.5 rotate-[-90deg]" />
          <p className="text-sm text-[var(--color-text-primary)]">{summary}</p>
        </div>

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
