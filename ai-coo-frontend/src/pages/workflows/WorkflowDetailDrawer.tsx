import { useState } from 'react'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { AlertCircle, CheckCircle2, ChevronDown, ChevronRight, Clock, Pause, Play, XCircle } from 'lucide-react'
import {
  workflowService,
  ALL_TRIGGER_TYPES,
  conditionsToRuleList,
  isConditionGroup,
  describeLifetime,
  type RunStatus,
  type WorkflowStatus,
  type WorkflowRun,
} from '@/services/workflows'
import Modal from '@/components/ui/Modal'
import Badge from '@/components/ui/Badge'
import Skeleton from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import { Button } from '@/components/ui/Button'

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-alert-dim bg-alert-dim px-3 py-2 text-xs text-alert">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

function requestErrorMessage(error: unknown): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : 'Workflow run failed. Please try again.'
}

function runStatusBadge(status: RunStatus) {
  const map: Record<RunStatus, { tone: 'signal' | 'alert' | 'amber'; icon: typeof CheckCircle2 }> = {
    success: { tone: 'signal', icon: CheckCircle2 },
    partial_failure: { tone: 'alert', icon: XCircle },
    skipped_conditions: { tone: 'amber', icon: Clock },
  }
  const { tone, icon: Icon } = map[status]
  return (
    <Badge tone={tone}>
      <Icon size={11} className="mr-1 inline" />
      {status.replace('_', ' ')}
    </Badge>
  )
}

function triggerLabel(trigger: string) {
  return ALL_TRIGGER_TYPES.find((t) => t.value === trigger)?.label ?? trigger
}

function workflowStatusBadge(status: WorkflowStatus) {
  const map: Record<WorkflowStatus, { tone: 'signal' | 'amber' | 'neutral'; icon: typeof CheckCircle2 }> = {
    active: { tone: 'signal', icon: CheckCircle2 },
    paused: { tone: 'amber', icon: Pause },
    completed: { tone: 'neutral', icon: CheckCircle2 },
    expired: { tone: 'neutral', icon: Clock },
  }
  const { tone, icon: Icon } = map[status]
  return (
    <Badge tone={tone}>
      <Icon size={11} className="mr-1 inline" />
      {status}
    </Badge>
  )
}

function RunLogEntry({ run }: { run: WorkflowRun }) {
  const [expanded, setExpanded] = useState(false)
  const hasContext = run.trigger_context && Object.keys(run.trigger_context).length > 0

  return (
    <div className="px-3 py-3 flex flex-col gap-2">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 text-xs text-text-muted">
          {runStatusBadge(run.status)}
          <span>{new Date(run.executed_at).toLocaleString()}</span>
          {run.duration_ms != null && (
            <span className="text-text-faint">· {run.duration_ms}ms</span>
          )}
        </div>
        {hasContext && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="flex items-center gap-1 text-xs text-signal hover:underline"
          >
            {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            Trigger context
          </button>
        )}
      </div>

      {expanded && hasContext && (
        <pre className="text-[11px] leading-relaxed text-text-muted bg-surface border border-border rounded-md p-2 overflow-x-auto">
          {JSON.stringify(run.trigger_context, null, 2)}
        </pre>
      )}

      {run.error_message && (
        <p className="text-xs text-alert">{run.error_message}</p>
      )}

      {run.actions_executed.length > 0 && (
        <div className="flex flex-col gap-1">
          {run.actions_executed.map((a, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              {a.error ? (
                <XCircle size={12} className="text-alert shrink-0 mt-0.5" />
              ) : (
                <CheckCircle2 size={12} className="text-signal shrink-0 mt-0.5" />
              )}
              <div className="min-w-0">
                <span className="text-text-primary font-mono">{a.action}</span>
                {a.error ? (
                  <span className="text-alert ml-2">{a.error}</span>
                ) : a.result && Object.keys(a.result).length > 0 ? (
                  <span className="text-text-faint ml-2 font-mono break-all">
                    {JSON.stringify(a.result)}
                  </span>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}

      {run.status === 'skipped_conditions' && (
        <p className="text-xs text-text-faint">
          Conditions didn't match the test context, so no actions ran.
        </p>
      )}
    </div>
  )
}

interface WorkflowDetailDrawerProps {
  open: boolean
  orgId: string
  workflowId: string | null
  onClose: () => void
}

export default function WorkflowDetailDrawer({ open, orgId, workflowId, onClose }: WorkflowDetailDrawerProps) {
  const queryClient = useQueryClient()

  const { data: workflow, isLoading, isError } = useQuery({
    queryKey: ['workflows', 'detail', workflowId],
    queryFn: () => workflowService.getWorkflow(workflowId!, orgId),
    enabled: open && !!workflowId,
  })

  const runNowMutation = useMutation({
    mutationFn: () => workflowService.runNow(workflowId!, orgId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows', 'detail', workflowId] })
      queryClient.invalidateQueries({ queryKey: ['workflows', 'list'] })
    },
  })

  const conditionRules = workflow ? conditionsToRuleList(workflow.conditions) : []
  const conditionLogic = workflow && isConditionGroup(workflow.conditions) ? workflow.conditions.logic : 'AND'

  return (
    <Modal open={open} onClose={onClose} title={workflow ? workflow.name : 'Workflow details'}>
      <div className="flex flex-col gap-6 max-h-[75vh] overflow-y-auto pr-1">
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        ) : isError || !workflow ? (
          <ErrorBanner message="Couldn't load this workflow." />
        ) : (
          <>
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-2 text-sm text-text-muted flex-wrap">
                {workflowStatusBadge(workflow.status)}
                <span className="text-text-primary">{triggerLabel(workflow.trigger_type)}</span>
                {' · '}
                {workflow.actions.length} action{workflow.actions.length !== 1 ? 's' : ''}
              </div>
              <Button
                variant="secondary"
                loading={runNowMutation.isPending}
                disabled={workflow.status !== 'active'}
                onClick={() => runNowMutation.mutate()}
              >
                <Play size={13} />
                Run now
              </Button>
            </div>
            <p className="text-xs text-text-faint -mt-4">{describeLifetime(workflow)}</p>
            {(workflow.status === 'completed' || workflow.status === 'expired') && (
              <p className="text-xs text-text-faint">
                This workflow is {workflow.status} and won't run again{workflow.status === 'expired' ? '' : ' automatically'}.
              </p>
            )}

            {runNowMutation.isSuccess && (
              <div
                className={
                  runNowMutation.data.status === 'success'
                    ? 'rounded-lg border border-signal-dim bg-signal-dim px-3 py-2 text-xs text-signal'
                    : runNowMutation.data.status === 'partial_failure'
                    ? 'rounded-lg border border-alert-dim bg-alert-dim px-3 py-2 text-xs text-alert'
                    : 'rounded-lg border border-border bg-surface px-3 py-2 text-xs text-text-muted'
                }
              >
                Run {runNowMutation.data.status.replace('_', ' ')}
                {runNowMutation.data.duration_ms != null ? ` in ${runNowMutation.data.duration_ms}ms` : ''}
                {runNowMutation.data.error_message ? ` — ${runNowMutation.data.error_message}` : ''}
              </div>
            )}
            {runNowMutation.isError && <ErrorBanner message={requestErrorMessage(runNowMutation.error)} />}

            <div>
              <h3 className="text-sm font-medium text-text-primary mb-2">Conditions</h3>
              {conditionRules.length === 0 ? (
                <p className="text-xs text-text-faint">Runs on every matching event.</p>
              ) : (
                <div className="flex flex-col gap-1">
                  {conditionRules.length > 1 && (
                    <p className="text-xs text-text-faint mb-1">Match {conditionLogic} of:</p>
                  )}
                  {conditionRules.map((rule, i) => (
                    <p key={i} className="text-xs text-text-muted font-mono">
                      {rule.field} {rule.op === 'in' ? 'in' : '='}{' '}
                      {Array.isArray(rule.value) ? rule.value.join(', ') : rule.value}
                    </p>
                  ))}
                </div>
              )}
            </div>

            <div>
              <h3 className="text-sm font-medium text-text-primary mb-2">Actions</h3>
              <div className="flex flex-wrap gap-1.5">
                {workflow.actions.map((a) => (
                  <Badge key={a} tone="neutral">{a}</Badge>
                ))}
              </div>
            </div>

            <div>
              <h3 className="text-sm font-medium text-text-primary mb-2">Execution history</h3>
              {workflow.recent_runs.length === 0 ? (
                <EmptyState icon={Clock} title="No runs yet" description="Runs will appear here once this workflow fires, or you use Run now." />
              ) : (
                <div className="divide-y divide-border border border-border rounded-lg">
                  {workflow.recent_runs.map((run) => (
                    <RunLogEntry key={run.id} run={run} />
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
