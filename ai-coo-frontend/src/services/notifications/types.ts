export interface Notification {
  id: string
  title: string
  body: string
  read: boolean
  created_at: string
}

export interface NotificationsService {
  list(orgId: string): Promise<Notification[]>
  markRead(id: string): Promise<void>
  markAllRead(orgId: string): Promise<void>
}
