import { apiClient } from '@/api/client'
import type { Integration, IntegrationProvider, IntegrationsService } from './types'

export const realIntegrationsService: IntegrationsService = {
  list: (orgId) =>
    apiClient.get<Integration[]>('/integrations', { params: { org_id: orgId } }).then((r) => r.data),

  getLoginUrl: (provider: IntegrationProvider) =>
    apiClient.get<{ url: string }>(`/${provider}/login`).then((r) => r.data.url),

  disconnect: (provider, orgId) =>
    apiClient
      .post(`/${provider}/disconnect`, undefined, { params: { org_id: orgId } })
      .then(() => undefined),
}
