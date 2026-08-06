import { apiClient } from '@/api/client'
import type {
  Workflow,
  WorkflowRun,
  WorkflowService,
  WorkflowWithRuns,
} from './types'

export const realWorkflowService: WorkflowService = {
  listWorkflows: (orgId) =>
    apiClient.get<Workflow[]>('/workflows', { params: { org_id: orgId } }).then((r) => r.data),

  getWorkflow: (workflowId, orgId) =>
    apiClient
      .get<WorkflowWithRuns>(`/workflows/${workflowId}`, { params: { org_id: orgId } })
      .then((r) => r.data),

  createWorkflow: (payload) =>
    apiClient
      .post<{ status: string; workflow: Workflow }>('/workflows', payload)
      .then((r) => r.data.workflow),

  updateWorkflow: (workflowId, orgId, payload) =>
    apiClient
      .patch<{ status: string; workflow: Workflow }>(`/workflows/${workflowId}`, payload, {
        params: { org_id: orgId },
      })
      .then((r) => r.data.workflow),

  deleteWorkflow: (workflowId, orgId) =>
    apiClient.delete(`/workflows/${workflowId}`, { params: { org_id: orgId } }).then(() => undefined),

  runNow: (workflowId, orgId, contextOverride) =>
    apiClient
      .post<{ status: string; run: WorkflowRun }>(
        `/workflows/${workflowId}/run-now`,
        contextOverride ?? undefined,
        { params: { org_id: orgId } }
      )
      .then((r) => r.data.run),
}
