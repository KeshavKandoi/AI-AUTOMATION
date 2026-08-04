import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Calendar as CalendarIcon, Sparkles, Plus, AlertCircle, Clock,
  UtensilsCrossed, Play, CheckCircle2,
} from 'lucide-react'
import { calendarService, type LunchBlockSettings } from '@/services/calendar'
import { useAuthStore } from '@/store/authStore'
import Card from '@/components/ui/Card'
import Skeleton from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import Modal from '@/components/ui/Modal'
import Badge from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-[var(--color-alert-dim)] bg-[var(--color-alert-dim)] px-3 py-2 text-xs text-[var(--color-alert)]">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

function formatEventTime(iso: string | null) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
    })
  } catch {
    return iso
  }
}

const DEFAULT_LUNCH_SETTINGS = {
  enabled: true,
  start_time: '13:00:00',
  end_time: '14:00:00',
  title: 'Lunch',
  weekdays_only: true,
}

export default function CalendarPage() {
  const orgId = useAuthStore((s) => s.user?.organization_id)
  const queryClient = useQueryClient()

  const [summaryRequested, setSummaryRequested] = useState(false)
  const [eventModalOpen, setEventModalOpen] = useState(false)
  const [eventTitle, setEventTitle] = useState('')
  const [eventStart, setEventStart] = useState('')
  const [eventEnd, setEventEnd] = useState('')

  const [lunchForm, setLunchForm] = useState<Omit<LunchBlockSettings, 'organization_id'> | null>(null)

  const { data: events, isLoading: eventsLoading, isError: eventsError } = useQuery({
    queryKey: ['calendar', 'events', orgId],
    queryFn: () => calendarService.getEvents(orgId!),
    enabled: !!orgId,
    retry: false,
  })

  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
    refetch: fetchSummary,
  } = useQuery({
    queryKey: ['calendar', 'summary', orgId],
    queryFn: () => calendarService.getSummary(orgId!),
    enabled: false,
    retry: false,
  })

  const {
    data: lunchSettings,
    isLoading: lunchLoading,
  } = useQuery({
    queryKey: ['calendar', 'lunch-settings', orgId],
    queryFn: () => calendarService.getLunchBlockSettings(orgId!),
    enabled: !!orgId,
    retry: false,
  })

  useEffect(() => {
    if (lunchSettings && !lunchForm) {
      setLunchForm({
        enabled: lunchSettings.enabled,
        start_time: lunchSettings.start_time,
        end_time: lunchSettings.end_time,
        title: lunchSettings.title,
        weekdays_only: lunchSettings.weekdays_only,
      })
    }
  }, [lunchSettings, lunchForm])

  const createEventMutation = useMutation({
    mutationFn: () =>
      calendarService.createEvent(
        orgId!,
        eventTitle,
        new Date(eventStart).toISOString(),
        new Date(eventEnd).toISOString()
      ),
    onSuccess: () => {
      setEventModalOpen(false)
      setEventTitle('')
      setEventStart('')
      setEventEnd('')
      queryClient.invalidateQueries({ queryKey: ['calendar', 'events', orgId] })
    },
  })

  const saveLunchSettingsMutation = useMutation({
    mutationFn: (settings: Omit<LunchBlockSettings, 'organization_id'>) =>
      calendarService.upsertLunchBlockSettings({ organization_id: orgId!, ...settings }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar', 'lunch-settings', orgId] })
    },
  })

  const runLunchNowMutation = useMutation({
    mutationFn: () => calendarService.runLunchBlockNow(orgId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar', 'lunch-settings', orgId] })
      queryClient.invalidateQueries({ queryKey: ['calendar', 'events', orgId] })
    },
  })

  const handleLoadSummary = () => {
    setSummaryRequested(true)
    fetchSummary()
  }

  const activeLunchForm = lunchForm ?? DEFAULT_LUNCH_SETTINGS

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
            Google Calendar
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Upcoming events and automated scheduling
          </p>
        </div>
        <Button onClick={() => setEventModalOpen(true)}>
          <Plus size={15} />
          New event
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Upcoming events */}
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-4">
            <CalendarIcon size={16} className="text-[var(--color-signal)]" />
            <h2 className="text-sm font-medium text-[var(--color-text-primary)]">
              Upcoming events {events && <span className="text-[var(--color-text-faint)]">({events.length})</span>}
            </h2>
          </div>
          {eventsLoading ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : eventsError ? (
            <ErrorBanner message="Couldn't load events." />
          ) : !events || events.length === 0 ? (
            <EmptyState icon={CalendarIcon} title="No upcoming events" />
          ) : (
            <div className="divide-y divide-[var(--color-border)]">
              {events.map((event, idx) => (
                <div key={idx} className="py-2.5">
                  <p className="text-sm text-[var(--color-text-primary)]">{event.summary || 'Untitled event'}</p>
                  <p className="text-xs text-[var(--color-text-faint)] mt-0.5">
                    {formatEventTime(event.start)}
                    {event.end && ` – ${formatEventTime(event.end)}`}
                  </p>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* AI Summary */}
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles size={16} className="text-[var(--color-amber)]" />
            <h2 className="text-sm font-medium text-[var(--color-text-primary)]">AI summary</h2>
          </div>
          {!summaryRequested ? (
            <div className="flex flex-col items-center justify-center py-6">
              <p className="text-xs text-[var(--color-text-faint)] mb-3 text-center">
                Get an AI-generated overview of your schedule
              </p>
              <Button variant="secondary" onClick={handleLoadSummary}>
                <Sparkles size={14} />
                Load AI summary
              </Button>
            </div>
          ) : summaryLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          ) : summaryError ? (
            <div className="flex flex-col gap-2">
              <ErrorBanner message="Couldn't load AI summary." />
              <Button variant="ghost" onClick={() => fetchSummary()}>
                Try again
              </Button>
            </div>
          ) : (
            <p className="text-sm text-[var(--color-text-muted)] whitespace-pre-line leading-relaxed">
              {summary}
            </p>
          )}
        </Card>
      </div>

      {/* Lunch Block Automation */}
      <Card className="p-5">
        <div className="flex items-center gap-2 mb-4">
          <UtensilsCrossed size={16} className="text-[var(--color-signal)]" />
          <h2 className="text-sm font-medium text-[var(--color-text-primary)]">Lunch block automation</h2>
        </div>

        {lunchLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-full" />
          </div>
        ) : (
          <>
            <p className="text-xs text-[var(--color-text-faint)] mb-4">
              Automatically blocks your calendar for lunch each day if no event already exists.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
              <Input
                label="Event title"
                value={activeLunchForm.title}
                onChange={(e) => setLunchForm({ ...activeLunchForm, title: e.target.value })}
              />
              <div className="flex items-end gap-2">
                <label className="flex items-center gap-2 text-sm text-[var(--color-text-muted)] pb-2.5">
                  <input
                    type="checkbox"
                    checked={activeLunchForm.enabled}
                    onChange={(e) => setLunchForm({ ...activeLunchForm, enabled: e.target.checked })}
                    className="rounded border-[var(--color-border)]"
                  />
                  Enabled
                </label>
                <label className="flex items-center gap-2 text-sm text-[var(--color-text-muted)] pb-2.5">
                  <input
                    type="checkbox"
                    checked={activeLunchForm.weekdays_only}
                    onChange={(e) => setLunchForm({ ...activeLunchForm, weekdays_only: e.target.checked })}
                    className="rounded border-[var(--color-border)]"
                  />
                  Weekdays only
                </label>
              </div>
              <Input
                label="Start time"
                type="time"
                value={activeLunchForm.start_time.slice(0, 5)}
                onChange={(e) => setLunchForm({ ...activeLunchForm, start_time: `${e.target.value}:00` })}
              />
              <Input
                label="End time"
                type="time"
                value={activeLunchForm.end_time.slice(0, 5)}
                onChange={(e) => setLunchForm({ ...activeLunchForm, end_time: `${e.target.value}:00` })}
              />
            </div>

            <div className="flex gap-2 mb-4">
              <Button
                variant="secondary"
                loading={saveLunchSettingsMutation.isPending}
                onClick={() => saveLunchSettingsMutation.mutate(activeLunchForm)}
              >
                Save settings
              </Button>
              <Button
                variant="ghost"
                loading={runLunchNowMutation.isPending}
                onClick={() => runLunchNowMutation.mutate()}
              >
                <Play size={13} />
                Run now
              </Button>
            </div>

            {saveLunchSettingsMutation.isSuccess && (
              <p className="text-xs text-[var(--color-signal)] flex items-center gap-1 mb-2">
                <CheckCircle2 size={12} />
                Settings saved.
              </p>
            )}
            {saveLunchSettingsMutation.isError && (
              <div className="mb-2">
                <ErrorBanner message="Failed to save settings." />
              </div>
            )}
            {runLunchNowMutation.isSuccess && (
              <p className="text-xs text-[var(--color-signal)] flex items-center gap-1 mb-2">
                <CheckCircle2 size={12} />
                Run status: {runLunchNowMutation.data.status}
              </p>
            )}
            {runLunchNowMutation.isError && (
              <div className="mb-2">
                <ErrorBanner message="Failed to trigger run." />
              </div>
            )}

            {lunchSettings && lunchSettings.runs.length > 0 && (
              <div className="mt-4">
                <p className="text-xs text-[var(--color-text-faint)] mb-2">Recent runs</p>
                <div className="divide-y divide-[var(--color-border)]">
                  {lunchSettings.runs.slice(0, 5).map((run) => (
                    <div key={run.id} className="flex items-center justify-between py-2">
                      <span className="text-xs text-[var(--color-text-muted)]">{run.run_date}</span>
                      <Badge tone={run.status === 'created' || run.status === 'already_exists' ? 'signal' : run.status === 'failed' ? 'alert' : 'neutral'}>
                        {run.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {!lunchSettings && (
              <p className="text-xs text-[var(--color-text-faint)] flex items-center gap-1">
                <Clock size={12} />
                No settings saved yet — configure and save above to get started.
              </p>
            )}
          </>
        )}
      </Card>

      {/* Create event modal */}
      <Modal open={eventModalOpen} onClose={() => setEventModalOpen(false)} title="New calendar event">
        <div className="flex flex-col gap-4">
          <Input
            label="Title"
            placeholder="Event title"
            value={eventTitle}
            onChange={(e) => setEventTitle(e.target.value)}
          />
          <Input
            label="Start"
            type="datetime-local"
            value={eventStart}
            onChange={(e) => setEventStart(e.target.value)}
          />
          <Input
            label="End"
            type="datetime-local"
            value={eventEnd}
            onChange={(e) => setEventEnd(e.target.value)}
          />
          {createEventMutation.isError && (
            <ErrorBanner message="Failed to create event. Check the details and try again." />
          )}
          <Button
            className="w-full"
            disabled={!eventTitle.trim() || !eventStart || !eventEnd}
            loading={createEventMutation.isPending}
            onClick={() => createEventMutation.mutate()}
          >
            Create event
          </Button>
        </div>
      </Modal>
    </div>
  )
}
