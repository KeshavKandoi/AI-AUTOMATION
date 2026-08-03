export interface Task {
  id: string
  organization_id: string
  title: string
  description: string
  priority: 'high' | 'medium' | 'low'
  status: string
  source: string
  created_at: string
  source_ref?: string | null
  resolution?: string | null
  closeout_status?: string | null
  closeout_error?: string | null
}
