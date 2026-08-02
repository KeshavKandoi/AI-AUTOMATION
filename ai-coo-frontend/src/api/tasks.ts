import { apiClient } from './client'
import type { Task } from '@/types/tasks'

export const tasksApi = {
  list: (orgId: string) =>
    apiClient.get<Task[]>('/tasks', { params: { org_id: orgId } }),

  pendingApproval: (orgId: string) =>
    apiClient.get<Task[]>('/tasks/pending-approval', { params: { org_id: orgId } }),

  approve: (taskId: string) =>
    apiClient.post(`/tasks/${taskId}/approve`),

  reject: (taskId: string) =>
    apiClient.post(`/tasks/${taskId}/reject`),
}
