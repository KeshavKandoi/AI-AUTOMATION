export interface CalendarEvent {
  summary: string | null
  start: string | null
  end: string | null
}

export interface CreateEventResult {
  status: string
  event_link: string
}

export interface LunchBlockSettings {
  id?: string
  organization_id: string
  enabled: boolean
  start_time: string
  end_time: string
  title: string
  weekdays_only: boolean
  created_at?: string
}

export interface LunchBlockRun {
  id: string
  organization_id: string
  run_date: string
  status: string
  event_id: string | null
  error_message: string | null
  executed_at: string
}

export interface LunchBlockSettingsWithRuns extends LunchBlockSettings {
  runs: LunchBlockRun[]
}

export interface CalendarService {
  getEvents(orgId: string): Promise<CalendarEvent[]>
  getSummary(orgId: string): Promise<string>
  createEvent(orgId: string, summary: string, startTime: string, endTime: string): Promise<CreateEventResult>
  getLunchBlockSettings(orgId: string): Promise<LunchBlockSettingsWithRuns | null>
  upsertLunchBlockSettings(settings: LunchBlockSettings): Promise<LunchBlockSettings>
  runLunchBlockNow(orgId: string): Promise<LunchBlockRun>
}
