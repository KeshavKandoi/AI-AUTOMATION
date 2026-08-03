export interface AuditLogEntry {
  id: string
  organization_id: string
  action: string
  metadata: Record<string, unknown>
  created_at: string
}

export interface AuditLogsService {
  list(orgId: string, limit?: number): Promise<AuditLogEntry[]>
}
