export type AuditStatus = 'success' | 'failed' | 'warning' | 'info'
export type ActorType = 'user' | 'ai' | 'system'

export interface AuditLogEntry {
  id: string
  organization_id: string
  module: string | null
  action: string
  status: AuditStatus | null
  summary: string | null
  user_id: string | null
  actor_type: ActorType | null
  resource_type: string | null
  resource_id: string | null
  metadata: Record<string, unknown> | null
  details: Record<string, unknown> | null
  error_message: string | null
  duration_ms: number | null
  source: string | null
  created_at: string
}

export interface AuditLogListResponse {
  items: AuditLogEntry[]
  total: number
  limit: number
  offset: number
}

export interface AuditLogFilters {
  module?: string
  action?: string
  status?: AuditStatus
  resource_type?: string
  resource_id?: string
  search?: string
  start_date?: string
  end_date?: string
  sort_dir?: 'asc' | 'desc'
}

export interface AuditLogFilterOptions {
  modules: string[]
  actions: string[]
}

export interface AuditLogsService {
  list(orgId: string, limit?: number, offset?: number, filters?: AuditLogFilters): Promise<AuditLogListResponse>
  get(logId: string): Promise<AuditLogEntry>
  getFilterOptions(orgId: string): Promise<AuditLogFilterOptions>
}
