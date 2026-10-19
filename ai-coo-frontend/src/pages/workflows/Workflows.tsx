import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, useReducedMotion } from 'framer-motion'
import { AlertCircle, ArrowRight, CheckCircle2, Clock, Pause, Play, Plus, Sparkles, Trash2, Workflow as WorkflowIcon } from 'lucide-react'
import {
  workflowService,
  ALL_TRIGGER_TYPES,
  summarizeConditions,
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
    <div className="flex items-start gap-2 rounded-lg border border-alert-dim bg-alert-dim px-3 py-2 text-xs text-alert">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

function statusBadge(status: WorkflowStatus) {
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

function triggerLabel(trigger: Workflow['trigger_type']) {
  return ALL_TRIGGER_TYPES.find((t) => t.value === trigger)?.label ?? trigger
}

export default function Workflows() {
  const orgId = useAuthStore((s) => s.user?.organization_id)
  const queryClient = useQueryClient()
  const reduceMotion = useReducedMotion()

  const [formOpen, setFormOpen] = useState(false)
  const [editingWorkflow, setEditingWorkflow] = useState<Workflow | null>(null)
  const [detailWorkflowId, setDetailWorkflowId] = useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [runNowFeedback, setRunNowFeedback] = useState<{ id: string; status?: RunStatus; error?: string } | null>(null)

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
      setRunNowFeedback({ id: workflowId, status: run.status, error: run.error_message ?? undefined })
      queryClient.invalidateQueries({ queryKey: ['workflows', 'detail', workflowId] })
    },
    onError: (error, workflowId) => {
      const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setRunNowFeedback({ id: workflowId, error: typeof detail === 'string' ? detail : 'Workflow run failed. Please try again.' })
    },
  })

  const sortedWorkflows = useMemo(() => {
    if (!workflows) return []
    const order: Record<WorkflowStatus, number> = { active: 0, paused: 1, completed: 2, expired: 3 }
    return [...workflows].sort((a, b) => order[a.status] - order[b.status])
  }, [workflows])
  const activeCount = sortedWorkflows.filter((workflow) => workflow.status === 'active').length
  const pausedCount = sortedWorkflows.filter((workflow) => workflow.status === 'paused').length

  const openCreate = () => {
    setEditingWorkflow(null)
    setFormOpen(true)
  }

  const openEdit = (workflow: Workflow) => {
    setEditingWorkflow(workflow)
    setFormOpen(true)
  }

  return (
    <div className="relative isolate mx-auto flex max-w-7xl flex-col gap-6 overflow-hidden p-5 md:p-8">
      <div aria-hidden="true" className="pointer-events-none absolute -right-28 -top-36 -z-10 h-96 w-96 rounded-full bg-signal/6 blur-3xl" />
      <motion.header initial={reduceMotion ? false : { opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduceMotion ? 0 : 0.35 }} className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-signal/20 bg-signal-dim px-3 py-1 text-[11px] font-medium tracking-wide text-signal">
            <Sparkles size={13} /> AUTOMATION STUDIO
          </div>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-text-primary">
            Workflow Automations
          </h1>
          <p className="mt-1 text-sm text-text-muted">
            Automatically react to events with tasks, emails, and notifications
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus size={15} />
          New workflow
        </Button>
      </motion.header>

      {!isLoading && !isError && (
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Total workflows', value: sortedWorkflows.length, tone: 'text-text-primary' },
            { label: 'Active', value: activeCount, tone: 'text-signal' },
            { label: 'Paused', value: pausedCount, tone: 'text-amber' },
          ].map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={reduceMotion ? false : { opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: reduceMotion ? 0 : 0.28, delay: reduceMotion ? 0 : index * 0.06 }}
              className="rounded-2xl border border-border bg-surface/70 px-4 py-3.5 shadow-[0_16px_44px_-34px_rgba(0,0,0,0.8)]"
            >
              <p className="text-xs text-text-muted">{stat.label}</p>
              <p className={`mt-1 font-display text-2xl font-semibold ${stat.tone}`}>{stat.value}</p>
            </motion.div>
          ))}
        </div>
      )}

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
          {sortedWorkflows.map((workflow, index) => (
            <motion.div
              key={workflow.id}
              initial={reduceMotion ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              whileHover={reduceMotion ? undefined : { y: -2, borderColor: 'var(--color-border-hover)' }}
              transition={{ duration: reduceMotion ? 0 : 0.28, delay: reduceMotion ? 0 : Math.min(index * 0.045, 0.3) }}
              className="rounded-2xl border border-border bg-surface/70 p-5 shadow-[0_16px_44px_-34px_rgba(0,0,0,0.8)] backdrop-blur-xl"
            >
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      onClick={() => setDetailWorkflowId(workflow.id)}
                      className="text-sm font-medium text-text-primary hover:underline"
                    >
                      {workflow.name}
                    </button>
                    {statusBadge(workflow.status)}
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-text-muted">
                    <span className="rounded-lg border border-border bg-surface-hover px-2.5 py-1.5">{triggerLabel(workflow.trigger_type)}</span>
                    <ArrowRight size={12} className="text-text-faint" />
                    <span className="rounded-lg border border-border bg-surface-hover px-2.5 py-1.5">{summarizeConditions(workflow.conditions)}</span>
                    <ArrowRight size={12} className="text-text-faint" />
                    <span className="rounded-lg border border-signal/25 bg-signal-dim px-2.5 py-1.5 text-signal">{workflow.actions.length} action{workflow.actions.length !== 1 ? 's' : ''}</span>
                  </div>
                  <p className="mt-2 text-xs text-text-faint">{workflow.actions.map((action) => action.replaceAll('_', ' ')).join(' · ')}</p>
                  {runNowFeedback?.id === workflow.id && runNowFeedback.error && (
                    <p className="text-xs text-alert mt-1">{runNowFeedback.error}</p>
                  )}
                  {runNowFeedback?.id === workflow.id && runNowFeedback.status && (
                    <p
                      className={
                        runNowFeedback.status === 'success'
                          ? 'text-xs text-signal mt-1'
                          : runNowFeedback.status === 'partial_failure'
                          ? 'text-xs text-alert mt-1'
                          : 'text-xs text-amber mt-1'
                      }
                    >
                      Run {runNowFeedback.status.replace('_', ' ')} — see details for logs.
                    </p>
                  )}
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                  {workflow.status === 'active' && (
                    <Button
                      variant="ghost"
                      loading={runNowMutation.isPending && runNowMutation.variables === workflow.id}
                      onClick={() => runNowMutation.mutate(workflow.id)}
                    >
                      <Play size={13} />
                      Run now
                    </Button>
                  )}
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
                      className="bg-alert! text-white!"
                      loading={deleteMutation.isPending}
                      onBlur={() => setConfirmDeleteId(null)}
                      onClick={() => deleteMutation.mutate(workflow.id)}
                    >
                      Confirm?
                    </Button>
                  ) : (
                    <button
                      onClick={() => setConfirmDeleteId(workflow.id)}
                      className="text-text-faint hover:text-alert transition-colors p-2"
                      title="Delete workflow"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </div>
            </motion.div>
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
