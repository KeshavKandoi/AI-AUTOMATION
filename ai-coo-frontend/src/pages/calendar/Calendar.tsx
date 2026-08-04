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
    mutationFn: () => calendarService.createEvent(orgId!, eventTitle, eventStart, eventEnd),
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
