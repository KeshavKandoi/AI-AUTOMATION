import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { AlertCircle, CheckCircle2, Clock, Play, XCircle } from 'lucide-react'
import { workflowService, ALL_TRIGGER_TYPES, type RunStatus, type WorkflowRun } from '@/services/workflows'
import Modal from '@/components/ui/Modal'
import Badge from '@/components/ui/Badge'
import Skeleton from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import { Button } from '@/components/ui/Button'

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-[var(--color-alert-dim)] bg-[var(--color-alert-dim)] px-3 py-2 text-xs text-[var(--color-alert)]">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
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

function RunLogEntry({ run }: { run: WorkflowRun }) {
  return (
    <div className="px-3 py-3 flex flex-col gap-2">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
          {runStatusBadge(run.status)}
          <span>{new Date(run.executed_at).toLocaleString()}</span>
        </div>
      </div>
      {run.error_message && (
        <p className="text-xs text-[var(--color-alert)]">{run.error_message}</p>
      )}
      {run.actions_executed.length > 0 && (
        <div className="flex flex-col gap-1">
          {run.actions_executed.map((a, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              {a.error ? (
                <XCircle size={12} className="text-[var(--color-alert)] shrink-0" />
              ) : (
                <CheckCircle2 size={12} className="text-[var(--color-signal)] shrink-0" />
              )}
              <span className="text-[var(--color-text-primary)] font-mono">{a.action}</span>
              {a.error && <span className="text-[var(--color-alert)] truncate">{a.error}</span>}
            </div>
          ))}
        </div>
      )}
      {run.status === 'skipped_conditions' && (
        <p className="text-xs text-[var(--color-text-faint)]">
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
              <div className="text-sm text-[var(--color-text-muted)]">
                <span className="text-[var(--color-text-primary)]">{triggerLabel(workflow.trigger_type)}</span>
                {' · '}
                {workflow.actions.length} action{workflow.actions.length !== 1 ? 's' : ''}
              </div>
              <Button variant="secondary" loading={runNowMutation.isPending} onClick={() => runNowMutation.mutate()}>
                <Play size={13} />
                Run now
              </Button>
            </div>

            {runNowMutation.isSuccess && (
              <div
                className={
                  runNowMutation.data.status === 'success'
                    ? 'rounded-lg border border-[var(--color-signal-dim)] bg-[var(--color-signal-dim)] px-3 py-2 text-xs text-[var(--color-signal)]'
                    : runNowMutation.data.status === 'partial_failure'
                    ? 'rounded-lg border border-[var(--color-alert-dim)] bg-[var(--color-alert-dim)] px-3 py-2 text-xs text-[var(--color-alert)]'
                    : 'rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-xs text-[var(--color-text-muted)]'
                }
              >
                Run {runNowMutation.data.status.replace('_', ' ')}
                {runNowMutation.data.error_message ? ` — ${runNowMutation.data.error_message}` : ''}
              </div>
            )}
            {runNowMutation.isError && <ErrorBanner message="Failed to trigger this run. Try again." />}

            <div>
              <h3 className="text-sm font-medium text-[var(--color-text-primary)] mb-2">Conditions</h3>
              {Object.keys(workflow.conditions ?? {}).length === 0 ? (
                <p className="text-xs text-[var(--color-text-faint)]">Runs on every matching event.</p>
              ) : (
                <div className="flex flex-col gap-1">
                  {Object.entries(workflow.conditions).map(([k, v]) => (
                    <p key={k} className="text-xs text-[var(--color-text-muted)] font-mono">
                      {k} = {v}
                    </p>
                  ))}
                </div>
              )}
            </div>

            <div>
              <h3 className="text-sm font-medium text-[var(--color-text-primary)] mb-2">Actions</h3>
              <div className="flex flex-wrap gap-1.5">
                {workflow.actions.map((a) => (
                  <Badge key={a} tone="neutral">{a}</Badge>
                ))}
              </div>
            </div>

            <div>
              <h3 className="text-sm font-medium text-[var(--color-text-primary)] mb-2">Execution history</h3>
              {workflow.recent_runs.length === 0 ? (
                <EmptyState icon={Clock} title="No runs yet" description="Runs will appear here once this workflow fires, or you use Run now." />
              ) : (
                <div className="divide-y divide-[var(--color-border)] border border-[var(--color-border)] rounded-lg">
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
