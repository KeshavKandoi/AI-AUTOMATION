import { apiClient } from '@/api/client'
import type { Integration, IntegrationProvider, IntegrationsService } from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string

export const realIntegrationsService: IntegrationsService = {
  list: (orgId) =>
    apiClient.get<Integration[]>('/integrations', { params: { org_id: orgId } }).then((r) => r.data),

  loginUrl: (provider: IntegrationProvider, orgId: string) =>
    `${API_BASE_URL}/${provider}/login?org_id=${encodeURIComponent(orgId)}`,
}
