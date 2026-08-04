import { apiClient } from '@/api/client'
import type { GmailService, GmailUnreadResult } from './types'

export const realGmailService: GmailService = {
  getUnread: (orgId) =>
    apiClient
      .get<GmailUnreadResult>('/gmail/unread', { params: { org_id: orgId } })
      .then((r) => r.data),

  getSummary: (orgId) =>
    apiClient
      .get<{ summary: string }>('/gmail/summary', { params: { org_id: orgId } })
      .then((r) => r.data.summary),
}
