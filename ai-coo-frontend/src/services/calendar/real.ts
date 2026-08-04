import { apiClient } from '@/api/client'
import type {
  CalendarEvent,
  CalendarService,
  CreateEventResult,
  LunchBlockRun,
  LunchBlockSettings,
  LunchBlockSettingsWithRuns,
} from './types'

export const realCalendarService: CalendarService = {
  getEvents: (orgId) =>
    apiClient
      .get<{ event_count: number; events: CalendarEvent[] }>('/calendar/events', { params: { org_id: orgId } })
      .then((r) => r.data.events),

  getSummary: (orgId) =>
    apiClient
      .get<{ summary: string }>('/calendar/summary', { params: { org_id: orgId } })
      .then((r) => r.data.summary),

  createEvent: (orgId, summary, startTime, endTime) =>
    apiClient
      .post<CreateEventResult>('/calendar/create-event', undefined, {
        params: { org_id: orgId, summary, start_time: startTime, end_time: endTime },
      })
      .then((r) => r.data),

  getLunchBlockSettings: (orgId) =>
    apiClient
      .get<LunchBlockSettingsWithRuns>('/lunch-block/settings', { params: { org_id: orgId } })
      .then((r) => r.data)
      .catch((err) => {
        if (err?.response?.status === 404) return null
        throw err
      }),

  upsertLunchBlockSettings: (settings) =>
    apiClient
      .post<{ status: string; settings: LunchBlockSettings }>('/lunch-block/settings', settings)
      .then((r) => r.data.settings),

  runLunchBlockNow: (orgId) =>
    apiClient
      .post<{ status: string; run: LunchBlockRun }>('/lunch-block/run-now', undefined, { params: { org_id: orgId } })
      .then((r) => r.data.run),
}
