import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Calendar as CalendarIcon, Sparkles, Plus, AlertCircle, CheckCircle2, Type } from 'lucide-react'
import { calendarService } from '@/services/calendar'
import { useAuthStore } from '@/store/authStore'
import Card from '@/components/ui/Card'
import Skeleton from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import Modal from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import DateTimePicker from '@/components/ui/DateTimePicker'

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

export default function CalendarPage() {
  const orgId = useAuthStore((s) => s.user?.organization_id)
  const queryClient = useQueryClient()

  const [summaryRequested, setSummaryRequested] = useState(false)
  const [eventModalOpen, setEventModalOpen] = useState(false)
  const [eventTitle, setEventTitle] = useState('')
  const [eventStart, setEventStart] = useState<Date | null>(null)
  const [eventEnd, setEventEnd] = useState<Date | null>(null)
  const [justCreated, setJustCreated] = useState(false)

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

  const createEventMutation = useMutation({
    mutationFn: () =>
      calendarService.createEvent(orgId!, eventTitle, eventStart!.toISOString(), eventEnd!.toISOString()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar', 'events', orgId] })
      setJustCreated(true)
      setEventTitle('')
      setEventStart(null)
      setEventEnd(null)
      setTimeout(() => {
        setEventModalOpen(false)
        setJustCreated(false)
      }, 1200)
    },
  })

  const handleLoadSummary = () => {
    setSummaryRequested(true)
    fetchSummary()
  }

  const closeModal = () => {
    setEventModalOpen(false)
    setEventTitle('')
    setEventStart(null)
    setEventEnd(null)
    createEventMutation.reset()
  }

  const canSubmit =
    eventTitle.trim().length > 0 && !!eventStart && !!eventEnd && eventEnd > eventStart

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
            Google Calendar
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Your upcoming events at a glance
          </p>
        </div>
        <Button onClick={() => setEventModalOpen(true)}>
          <Plus size={15} />
          New event
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
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

      <Modal open={eventModalOpen} onClose={closeModal} title="New event" className="max-w-md">
        {justCreated ? (
          <div className="flex flex-col items-center justify-center py-8 gap-3">
            <div className="h-12 w-12 rounded-full bg-[var(--color-signal-dim)] flex items-center justify-center">
              <CheckCircle2 size={22} className="text-[var(--color-signal)]" />
            </div>
            <p className="text-sm text-[var(--color-text-primary)] font-medium">Event created</p>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-[var(--color-text-muted)] flex items-center gap-1.5">
                <Type size={13} />
                Title
              </label>
              <Input
                placeholder="e.g. Team sync"
                value={eventTitle}
                onChange={(e) => setEventTitle(e.target.value)}
                autoFocus
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <DateTimePicker label="Starts" value={eventStart} onChange={setEventStart} />
              <DateTimePicker
                label="Ends"
                value={eventEnd}
                onChange={setEventEnd}
                minDate={eventStart ?? undefined}
              />
            </div>

            {eventStart && eventEnd && eventEnd <= eventStart && (
              <ErrorBanner message="End time must be after the start time." />
            )}
            {createEventMutation.isError && (
              <ErrorBanner message="Failed to create event. Please try again." />
            )}

            <Button
              className="w-full"
              disabled={!canSubmit}
              loading={createEventMutation.isPending}
              onClick={() => createEventMutation.mutate()}
            >
              Create event
            </Button>
          </div>
        )}
      </Modal>
    </div>
  )
}
