import { apiClient } from '@/api/client'
import type { AnalyticsService, AnalyticsSummary } from './types'

export const realAnalyticsService: AnalyticsService = {
  getSummary: (orgId, startDate, endDate) =>
    apiClient
      .get<AnalyticsSummary>('/analytics/summary', {
        params: { org_id: orgId, start_date: startDate, end_date: endDate },
      })
      .then((r) => r.data),
}
