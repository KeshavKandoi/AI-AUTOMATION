export interface Integration {
  id: string
  organization_id: string
  provider: 'github' | 'gmail' | 'discord' | string
  connected: boolean
  created_at: string
}
