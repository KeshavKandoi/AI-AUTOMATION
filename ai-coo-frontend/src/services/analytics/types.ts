export interface DateRange {
  start_date: string
  end_date: string
}

export interface DailyActivityPoint {
  date: string
  success: number
  failed: number
  warning: number
  info: number
}

export interface BreakdownItem {
  label: string
  count: number
}

export interface TaskMetrics {
  total: number
  open: number
  resolved: number
  by_priority: BreakdownItem[]
  by_status: BreakdownItem[]
}

export interface WorkflowMetrics {
  total_workflows: number
  active_workflows: number
  total_runs: number
  success_rate: number | null
  by_status: BreakdownItem[]
}

export interface CommitSchedulerMetrics {
  total_jobs: number
  active_jobs: number
  total_runs: number
  success_rate: number | null
  by_status: BreakdownItem[]
}

export interface AnalyticsSummary {
  date_range: DateRange
  total_events: number
  failed_events: number
  activity_trend: DailyActivityPoint[]
  module_breakdown: BreakdownItem[]
  tasks: TaskMetrics
  workflows: WorkflowMetrics
  commit_scheduler: CommitSchedulerMetrics
}

export type AnalyticsRangePreset = '7d' | '30d' | '90d'

export interface AnalyticsService {
  getSummary(orgId: string, startDate?: string, endDate?: string): Promise<AnalyticsSummary>
}
