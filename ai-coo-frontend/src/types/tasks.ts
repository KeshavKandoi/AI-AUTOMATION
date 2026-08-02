export interface Task {
  id: string
  organization_id: string
  title: string
  description: string
  priority: 'high' | 'medium' | 'low'
  status: string
  source: string
  created_at: string
}
