export interface AuditLog {
  id: string
  organization_id: string
  action: string
  details: Record<string, any>
  created_at: string
}
