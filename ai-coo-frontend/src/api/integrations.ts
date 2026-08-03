import { apiClient } from './client'
import type { Integration } from '@/types/integrations'

export const integrationsApi = {
  list: (orgId: string) =>
    apiClient.get<Integration[]>('/integrations', { params: { org_id: orgId } }),
}
