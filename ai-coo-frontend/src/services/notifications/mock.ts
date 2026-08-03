import type { Notification, NotificationsService } from './types'

let mockData: Notification[] = [
  {
    id: '1',
    title: 'GitHub issue resolved',
    body: 'Issue #12 in Smart-Inventory-Management-System was closed.',
    read: false,
    created_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
  },
  {
    id: '2',
    title: 'Scheduled commit succeeded',
    body: 'Daily commit job ran successfully.',
    read: false,
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
  },
  {
    id: '3',
    title: 'Calendar event created',
    body: 'Follow-up event added to your calendar.',
    read: true,
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 20).toISOString(),
  },
]

const delay = (ms = 400) => new Promise((resolve) => setTimeout(resolve, ms))

export const mockNotificationsService: NotificationsService = {
  list: async () => {
    await delay()
    return [...mockData].sort((a, b) => b.created_at.localeCompare(a.created_at))
  },
  markRead: async (id) => {
    await delay(200)
    mockData = mockData.map((n) => (n.id === id ? { ...n, read: true } : n))
  },
  markAllRead: async () => {
    await delay(200)
    mockData = mockData.map((n) => ({ ...n, read: true }))
  },
}
