export type NotificationPriority = 'low' | 'normal' | 'high' | 'urgent'

export interface NotificationEntry {
  id: string
  organization_id: string
  module: string
  category: string | null
  priority: string
  title: string
  body: string
  resource_type: string | null
  resource_id: string | null
  action_url: string | null
  action_label: string | null
  metadata: Record<string, unknown> | null
  delivered_channels: Record<string, unknown> | null
  read: boolean
  read_at: string | null
  created_at: string
}

export interface NotificationListResponse {
  items: NotificationEntry[]
  total: number
  unread_count: number
  limit: number
  offset: number
}

export interface NotificationFilters {
  module?: string
  category?: string
  unread_only?: boolean
}

export interface NotificationsService {
  list(orgId: string, limit?: number, offset?: number, filters?: NotificationFilters): Promise<NotificationListResponse>
  markRead(notificationId: string, orgId: string): Promise<NotificationEntry>
  markAllRead(orgId: string): Promise<number>
}
