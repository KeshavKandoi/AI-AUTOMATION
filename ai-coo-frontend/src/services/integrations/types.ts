export type IntegrationProvider = 'github' | 'gmail' | 'calendar'

export interface Integration {
  id: string
  organization_id: string
  provider: IntegrationProvider
  connected: boolean
  created_at: string
}

export interface IntegrationsService {
  list(orgId: string): Promise<Integration[]>
  getLoginUrl(provider: IntegrationProvider): Promise<string>
  disconnect(provider: IntegrationProvider, orgId: string): Promise<void>
}
