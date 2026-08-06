export type TriggerType = 'issue_created' | 'push' | 'pull_request_opened'
export type ActionName = 'create_task' | 'send_email' | 'notify_discord' | 'create_calendar_event' | 'save_audit_log'
export type WorkflowStatus = 'active' | 'paused'
export type RunStatus = 'success' | 'partial_failure' | 'skipped_conditions'
export type ConditionOp = 'eq' | 'in'
export type ConditionLogic = 'AND' | 'OR'

export interface ConditionRule {
  field: string
  op: ConditionOp
  value: string | string[]
}

export interface ConditionGroup {
  logic: ConditionLogic
  rules: ConditionRule[]
}

// Conditions can be the new group format, the legacy flat-dict format
// (still produced by workflows created before AND/OR support), or empty.
export type Conditions = ConditionGroup | Record<string, string> | Record<string, never>

export interface Workflow {
  id: string
  organization_id: string
  name: string
  trigger_type: TriggerType
  conditions: Conditions
  actions: ActionName[]
  status: WorkflowStatus
  created_at: string
}

export interface WorkflowActionResult {
  action: ActionName
  result?: Record<string, unknown>
  error?: string
}

export interface WorkflowRun {
  id: string
  workflow_id: string
  trigger_context: Record<string, unknown>
  actions_executed: WorkflowActionResult[]
  status: RunStatus
  error_message: string | null
  executed_at: string
  duration_ms: number | null
}

export interface WorkflowWithRuns extends Workflow {
  recent_runs: WorkflowRun[]
}

export interface CreateWorkflowPayload {
  organization_id: string
  name: string
  trigger_type: TriggerType
  conditions: Conditions
  actions: ActionName[]
}

export interface UpdateWorkflowPayload {
  name?: string
  conditions?: Conditions
  actions?: ActionName[]
  status?: WorkflowStatus
}

export interface WorkflowService {
  listWorkflows(orgId: string): Promise<Workflow[]>
  getWorkflow(workflowId: string, orgId: string): Promise<WorkflowWithRuns>
  createWorkflow(payload: CreateWorkflowPayload): Promise<Workflow>
  updateWorkflow(workflowId: string, orgId: string, payload: UpdateWorkflowPayload): Promise<Workflow>
  deleteWorkflow(workflowId: string, orgId: string): Promise<void>
  runNow(workflowId: string, orgId: string, contextOverride?: Record<string, unknown>): Promise<WorkflowRun>
}

export const ALL_TRIGGER_TYPES: { value: TriggerType; label: string; description: string }[] = [
  { value: 'issue_created', label: 'Issue created', description: 'Fires when a new GitHub issue is opened' },
  { value: 'push', label: 'Push', description: 'Fires when commits are pushed to a branch' },
  { value: 'pull_request_opened', label: 'Pull request opened', description: 'Fires when a new pull request is opened' },
]

export const ACTION_OPTIONS: { value: ActionName; label: string; description: string }[] = [
  { value: 'create_task', label: 'Create task', description: 'Adds a task to your task list' },
  { value: 'send_email', label: 'Send email', description: 'Emails your notification address via Gmail' },
  { value: 'notify_discord', label: 'Notify Discord', description: 'Posts a message to your Discord webhook' },
  { value: 'create_calendar_event', label: 'Create calendar event', description: 'Adds a 30-minute event to your calendar' },
  { value: 'save_audit_log', label: 'Save audit log', description: 'Records the event in your audit log' },
]

// Condition fields available per trigger, matching the real context shape each
// webhook path builds server-side. Keeping the builder in sync with these
// prevents selecting fields (like "priority" on a Push trigger) that don't exist
// on that trigger's context and could never match.
export const TRIGGER_FIELDS: Record<TriggerType, { field: string; label: string; example: string }[]> = {
  issue_created: [
    { field: 'priority', label: 'Priority', example: 'high' },
    { field: 'repo', label: 'Repository', example: 'my-org/my-repo' },
    { field: 'issue_number', label: 'Issue number', example: '42' },
    { field: 'title', label: 'Title', example: 'Bug: login fails' },
    { field: 'author', label: 'Author', example: 'octocat' },
    { field: 'assignee', label: 'Assignee', example: 'octocat' },
    { field: 'labels', label: 'Labels', example: 'bug' },
  ],
  push: [
    { field: 'repo', label: 'Repository', example: 'my-org/my-repo' },
    { field: 'branch', label: 'Branch', example: 'main' },
    { field: 'author', label: 'Author', example: 'octocat' },
    { field: 'commit_message', label: 'Commit message', example: 'fix: typo' },
    { field: 'commit_sha', label: 'Commit SHA', example: 'a1b2c3d' },
    { field: 'commit_count', label: 'Commit count', example: '1' },
  ],
  pull_request_opened: [
    { field: 'repo', label: 'Repository', example: 'my-org/my-repo' },
    { field: 'title', label: 'Title', example: 'Add login page' },
    { field: 'author', label: 'Author', example: 'octocat' },
    { field: 'source_branch', label: 'Source branch', example: 'feature/login' },
    { field: 'target_branch', label: 'Target branch', example: 'main' },
    { field: 'draft', label: 'Draft', example: 'false' },
    { field: 'labels', label: 'Labels', example: 'enhancement' },
  ],
}

export function isConditionGroup(conditions: Conditions): conditions is ConditionGroup {
  return conditions != null && 'rules' in conditions && 'logic' in conditions
}

export function conditionsToRuleList(conditions: Conditions): ConditionRule[] {
  if (!conditions) return []
  if (isConditionGroup(conditions)) return conditions.rules
  // Legacy flat dict -> treat each key as an eq rule
  return Object.entries(conditions as Record<string, string>).map(([field, value]) => ({
    field,
    op: 'eq' as ConditionOp,
    value,
  }))
}

export function summarizeConditions(conditions: Conditions): string {
  const rules = conditionsToRuleList(conditions)
  if (rules.length === 0) return 'Runs on every matching event'
  const logic = isConditionGroup(conditions) ? conditions.logic : 'AND'
  const parts = rules.map((r) => `${r.field} ${r.op === 'in' ? 'in' : '='} ${Array.isArray(r.value) ? r.value.join('/') : r.value}`)
  return parts.join(logic === 'OR' ? ' OR ' : ' AND ')
}
