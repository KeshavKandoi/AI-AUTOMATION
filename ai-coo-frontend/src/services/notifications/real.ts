import type { NotificationsService } from './types'

export const realNotificationsService: NotificationsService = {
  list: async () => {
    throw new Error('Notifications backend not implemented yet')
  },
  markRead: async () => {
    throw new Error('Notifications backend not implemented yet')
  },
  markAllRead: async () => {
    throw new Error('Notifications backend not implemented yet')
  },
}
