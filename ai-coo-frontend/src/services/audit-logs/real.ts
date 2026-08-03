import { apiClient } from '@/api/client'
import type { AuditLogEntry, AuditLogsService } from './types'

export const realAuditLogsService: AuditLogsService = {
  list: (orgId, limit = 50) =>
    apiClient
      .get<AuditLogEntry[]>('/audit-logs', { params: { org_id: orgId, limit } })
      .then((r) => r.data),
}
