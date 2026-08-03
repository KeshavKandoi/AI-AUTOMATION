import { apiClient } from './client'
import type { AuditLog } from '@/types/audit'

export const auditApi = {
  list: (orgId: string, limit = 10) =>
    apiClient.get<AuditLog[]>('/audit-logs', { params: { org_id: orgId, limit } }),
}
