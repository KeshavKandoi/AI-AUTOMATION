import { apiClient } from '@/api/client'
import type {
  AuditLogEntry,
  AuditLogFilterOptions,
  AuditLogFilters,
  AuditLogListResponse,
  AuditLogsService,
} from './types'

export const realAuditLogsService: AuditLogsService = {
  list: (orgId, limit = 50, offset = 0, filters = {}) =>
    apiClient
      .get<AuditLogListResponse>('/audit-logs', {
        params: { org_id: orgId, limit, offset, ...filters },
      })
      .then((r) => r.data),

  get: (logId) =>
    apiClient.get<AuditLogEntry>(`/audit-logs/${logId}`).then((r) => r.data),

  getFilterOptions: (orgId) =>
    apiClient
      .get<AuditLogFilterOptions>('/audit-logs/filters', { params: { org_id: orgId } })
      .then((r) => r.data),
}
