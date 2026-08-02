import { apiClient } from './client'

export interface SchedulerJob {
  id: string
  next_run: string
}

export interface SchedulerStatus {
  running: boolean
  jobs: SchedulerJob[]
}

export const schedulerApi = {
  status: () => apiClient.get<SchedulerStatus>('/scheduler/status'),
}
