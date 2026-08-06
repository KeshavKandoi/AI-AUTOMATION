import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, CheckCircle2, Clock, Pause, Play, Plus, Trash2, Workflow as WorkflowIcon } from 'lucide-react'
import {
  workflowService,
  ALL_TRIGGER_TYPES,
  type RunStatus,
  type Workflow,
  type WorkflowStatus,
} from '@/services/workflows'
import { useAuthStore } from '@/store/authStore'
import Card from '@/components/ui/Card'
import Skeleton from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import Badge from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import WorkflowFormModal from './WorkflowFormModal'
import WorkflowDetailDrawer from './WorkflowDetailDrawer'

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-[var(--color-alert-dim)] bg-[var(--color-alert-dim)] px-3 py-2 text-xs text-[var(--color-alert)]">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

function statusBadge(status: WorkflowStatus) {
  const map: Record<WorkflowStatus, { tone: 'signal' | 'amber'; icon: typeof CheckCircle2 }> = {
    active: { tone: 'signal', icon: CheckCircle2 },
    paused: { tone: 'amber', icon: Pause },
  }
  const { tone, icon: Icon } = map[status]
  return (
    <Badge tone={tone}>
      <Icon size={11} className="mr-1 inline" />
      {status}
    </Badge>
  )
}

function triggerLabel(trigger: Workflow['trigger_type']) {
  return ALL_TRIGGER_TYPES.find((t) => t.value === trigger)?.label ?? trigger
}

function conditionsSummary(conditions: Record<string, string>) {
  const entries = Object.entries(conditions ?? {})
  if (entries.length === 0) return 'Runs on every event'
  return entries.map(([k, v]) => `${k} = ${v}`).join(' · ')
}

function runStatusTone(status: RunStatus): 'signal' | 'alert' | 'amber' {
  if (status === 'success') return 'signal'
  if (status === 'partial_failure') return 'alert'
  return 'amber'
}

function LastRunIndicator({ workflowId, orgId }: { workflowId: string; orgId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['workflows', 'detail', workflowId],
    queryFn: () => workflowService.getWorkflow(workflowId, orgId),
  })

  if (isLoading) return <Skeleton className="h-4 w-24" />

  const lastRun = data?.recent_runs?.[0]
  if (!lastRun) {
    return <span className="text-xs text-[var(--color-text-faint)]">No runs yet</span>
  }

  return (
    <span className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)]">
      <Badge tone={runStatusTone(lastRun.status)}>{lastRun.status.replace('_', ' ')}</Badge>
      {new Date(lastRun.executed_at).toLocaleString()}
    </span>
  )
}

export default function Workflows() {
  const orgId = useAuthStore((s) => s.user?.organization_id)
  const queryClient = useQueryClient()

  const [formOpen, setFormOpen] = useState(false)
  const [editingWorkflow, setEditingWorkflow] = useState<Workflow | null>(null)
  const [detailWorkflowId, setDetailWorkflowId] = useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [runNowFeedback, setRunNowFeedback] = useState<{ id: string; status: RunStatus } | null>(null)

  const {
    data: workflows,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['workflows', 'list', orgId],
    queryFn: () => workflowService.listWorkflows(orgId!),
    enabled: !!orgId,
  })

  const toggleStatusMutation = useMutation({
    mutationFn: ({ workflow, status }: { workflow: Workflow; status: WorkflowStatus }) =>
      workflowService.updateWorkflow(workflow.id, orgId!, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows', 'list'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (workflowId: string) => workflowService.deleteWorkflow(workflowId, orgId!),
    onSuccess: () => {
      setConfirmDeleteId(null)
      queryClient.invalidateQueries({ queryKey: ['workflows', 'list'] })
    },
  })

  const runNowMutation = useMutation({
    mutationFn: (workflowId: string) => workflowService.runNow(workflowId, orgId!),
    onSuccess: (run, workflowId) => {
      setRunNowFeedback({ id: workflowId, status: run.status })
      queryClient.invalidateQueries({ queryKey: ['workflows', 'detail', workflowId] })
    },
  })

  const sortedWorkflows = useMemo(() => {
    if (!workflows) return []
    const order: Record<WorkflowStatus, number> = { active: 0, paused: 1 }
    return [...workflows].sort((a, b) => order[a.status] - order[b.status])
  }, [workflows])

  const openCreate = () => {
    setEditingWorkflow(null)
    setFormOpen(true)
  }

  const openEdit = (workflow: Workflow) => {
    setEditingWorkflow(workflow)
    setFormOpen(true)
  }

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
            Workflow Automations
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Automatically react to events with tasks, emails, and notifications
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus size={15} />
          New workflow
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : isError ? (
        <ErrorBanner message="Couldn't load workflows." />
      ) : sortedWorkflows.length === 0 ? (
        <Card className="p-8">
          <EmptyState
            icon={WorkflowIcon}
            title="No workflows yet"
            description="Create one to automatically respond to events like new GitHub issues."
          />
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {sortedWorkflows.map((workflow) => (
            <Card key={workflow.id} className="p-5">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      onClick={() => setDetailWorkflowId(workflow.id)}
                      className="text-sm font-medium text-[var(--color-text-primary)] hover:underline"
                    >
                      {workflow.name}
                    </button>
                    <Badge tone="neutral">{triggerLabel(workflow.trigger_type)}</Badge>
                    {statusBadge(workflow.status)}
                  </div>
                  <p className="text-xs text-[var(--color-text-muted)] mt-1">
                    {conditionsSummary(workflow.conditions)}
                  </p>
                  <p className="text-xs text-[var(--color-text-faint)] mt-1">
                    {workflow.actions.length} action{workflow.actions.length !== 1 ? 's' : ''} ·{' '}
                    {workflow.actions.join(', ')}
                  </p>
                  <div className="mt-2">
                    <LastRunIndicator workflowId={workflow.id} orgId={orgId!} />
                  </div>
                  {runNowFeedback?.id === workflow.id && (
                    <p
                      className={
                        runNowFeedback.status === 'success'
                          ? 'text-xs text-[var(--color-signal)] mt-1'
                          : runNowFeedback.status === 'partial_failure'
                          ? 'text-xs text-[var(--color-alert)] mt-1'
                          : 'text-xs text-[var(--color-amber)] mt-1'
                      }
                    >
                      Run {runNowFeedback.status.replace('_', ' ')} — see details for logs.
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    variant="ghost"
                    loading={runNowMutation.isPending && runNowMutation.variables === workflow.id}
                    onClick={() => runNowMutation.mutate(workflow.id)}
                  >
                    <Play size={13} />
                    Run now
                  </Button>
                  <Button variant="ghost" onClick={() => setDetailWorkflowId(workflow.id)}>
                    <Clock size={13} />
                    Details
                  </Button>
                  <Button variant="ghost" onClick={() => openEdit(workflow)}>
                    Edit
                  </Button>
                  {workflow.status === 'active' ? (
                    <Button
                      variant="ghost"
                      loading={toggleStatusMutation.isPending}
                      onClick={() => toggleStatusMutation.mutate({ workflow, status: 'paused' })}
                    >
                      <Pause size={13} />
                      Pause
                    </Button>
                  ) : (
                    <Button
                      variant="ghost"
                      loading={toggleStatusMutation.isPending}
                      onClick={() => toggleStatusMutation.mutate({ workflow, status: 'active' })}
                    >
                      <Play size={13} />
                      Resume
                    </Button>
                  )}
                  {confirmDeleteId === workflow.id ? (
                    <Button
                      variant="primary"
                      className="!bg-[var(--color-alert)] !text-white"
                      loading={deleteMutation.isPending}
                      onBlur={() => setConfirmDeleteId(null)}
                      onClick={() => deleteMutation.mutate(workflow.id)}
                    >
                      Confirm?
                    </Button>
                  ) : (
                    <button
                      onClick={() => setConfirmDeleteId(workflow.id)}
                      className="text-[var(--color-text-faint)] hover:text-[var(--color-alert)] transition-colors p-2"
                      title="Delete workflow"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <WorkflowFormModal
        open={formOpen}
        orgId={orgId ?? ''}
        workflow={editingWorkflow}
        onClose={() => setFormOpen(false)}
        onSuccess={() => setFormOpen(false)}
      />

      <WorkflowDetailDrawer
        open={!!detailWorkflowId}
        orgId={orgId ?? ''}
        workflowId={detailWorkflowId}
        onClose={() => setDetailWorkflowId(null)}
      />
    </div>
  )
}
