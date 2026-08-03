import { mockNotificationsService } from './mock'
import { realNotificationsService } from './real'
import { useMockFor } from '../config'

export * from './types'
export const notificationsService = useMockFor('notifications')
  ? mockNotificationsService
  : realNotificationsService
