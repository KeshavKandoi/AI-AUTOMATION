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

  resolveGithub: (taskId: string, resolution: 'resolved' | 'commented' = 'resolved') =>
    apiClient.post(`/tasks/${taskId}/approve-and-create-issue`, undefined, {
      params: { resolution },
    }),

  resolveGmail: (taskId: string, archive = false) =>
    apiClient.post(`/tasks/${taskId}/approve-and-send-email`, undefined, {
      params: { archive },
    }),

  resolveCalendar: (taskId: string, startTime: string, endTime: string) =>
    apiClient.post(`/tasks/${taskId}/approve-and-create-event`, undefined, {
      params: { start_time: startTime, end_time: endTime },
    }),
}
