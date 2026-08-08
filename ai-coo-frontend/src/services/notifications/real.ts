import { apiClient } from '@/api/client'
import type { NotificationEntry, NotificationFilters, NotificationListResponse, NotificationsService } from './types'

export const realNotificationsService: NotificationsService = {
  list: (orgId, limit = 50, offset = 0, filters = {}) =>
    apiClient
      .get<NotificationListResponse>('/notifications', { params: { org_id: orgId, limit, offset, ...filters } })
      .then((r) => r.data),

  markRead: (notificationId, orgId) =>
    apiClient
      .post<{ status: string; notification: NotificationEntry }>(
        `/notifications/${notificationId}/read`,
        undefined,
        { params: { org_id: orgId } }
      )
      .then((r) => r.data.notification),

  markAllRead: (orgId) =>
    apiClient
      .post<{ status: string; count: number }>('/notifications/mark-all-read', undefined, { params: { org_id: orgId } })
      .then((r) => r.data.count),
}
