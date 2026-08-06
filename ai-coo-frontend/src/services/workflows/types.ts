export type TriggerType = 'issue_created' | 'pr_opened' | 'push'
export type ActionName = 'create_task' | 'send_email' | 'notify_discord' | 'create_calendar_event' | 'save_audit_log'
export type WorkflowStatus = 'active' | 'paused'
export type RunStatus = 'success' | 'partial_failure' | 'skipped_conditions'

export interface Workflow {
  id: string
  organization_id: string
  name: string
  trigger_type: TriggerType
  conditions: Record<string, string>
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
}

export interface WorkflowWithRuns extends Workflow {
  recent_runs: WorkflowRun[]
}

export interface CreateWorkflowPayload {
  organization_id: string
  name: string
  trigger_type: TriggerType
  conditions: Record<string, string>
  actions: ActionName[]
}

export interface UpdateWorkflowPayload {
  name?: string
  conditions?: Record<string, string>
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

// Only trigger actually wired to the execution engine today.
// pr_opened / push are defined in the backend schema but have no dispatch call site yet,
// so the builder must not let users configure workflows against them.
export const LIVE_TRIGGER_TYPES: TriggerType[] = ['issue_created']

export const ALL_TRIGGER_TYPES: { value: TriggerType; label: string }[] = [
  { value: 'issue_created', label: 'Issue created' },
  { value: 'pr_opened', label: 'Pull request opened' },
  { value: 'push', label: 'Push' },
]

export const ACTION_OPTIONS: { value: ActionName; label: string; description: string }[] = [
  { value: 'create_task', label: 'Create task', description: 'Adds a task to your task list' },
  { value: 'send_email', label: 'Send email', description: 'Emails your notification address via Gmail' },
  { value: 'notify_discord', label: 'Notify Discord', description: 'Posts a message to your Discord webhook' },
  { value: 'create_calendar_event', label: 'Create calendar event', description: 'Adds a 30-minute event to your calendar' },
  { value: 'save_audit_log', label: 'Save audit log', description: 'Records the event in your audit log' },
]

// Fields available on the issue_created trigger context, for the condition builder.
export const ISSUE_CREATED_FIELDS = ['priority', 'repo', 'issue_number', 'title'] as const
