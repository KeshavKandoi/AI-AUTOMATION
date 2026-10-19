import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/Button'

interface DateTimePickerProps {
  label: string
  value: Date | null
  onChange: (date: Date) => void
  minDate?: Date
}

const WEEKDAY_LABELS = ['S', 'M', 'T', 'W', 'T', 'F', 'S']

function startOfDay(d: Date) {
  const copy = new Date(d)
  copy.setHours(0, 0, 0, 0)
  return copy
}

function isSameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}

function buildMonthGrid(viewDate: Date): (Date | null)[] {
  const year = viewDate.getFullYear()
  const month = viewDate.getMonth()
  const firstDay = new Date(year, month, 1)
  const startWeekday = firstDay.getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()

  const cells: (Date | null)[] = []
  for (let i = 0; i < startWeekday; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(year, month, d))
  return cells
}

function toTimeInputValue(d: Date) {
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${h}:${m}`
}

export default function DateTimePicker({ label, value, onChange, minDate }: DateTimePickerProps) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState({ top: 0, left: 0, width: 280, maxHeight: 380 })
  const min = minDate ?? new Date()

  const [viewMonth, setViewMonth] = useState(() => {
    const base = value ?? min
    return new Date(base.getFullYear(), base.getMonth(), 1)
  })
  const [pendingDate, setPendingDate] = useState<Date | null>(value ? startOfDay(value) : null)
  const [pendingTime, setPendingTime] = useState<string>(value ? toTimeInputValue(value) : '09:00')

  useLayoutEffect(() => {
    if (!open) return
    const updatePosition = () => {
      const anchor = triggerRef.current?.getBoundingClientRect()
      if (!anchor) return
      const viewport = window.visualViewport
      const top = viewport?.offsetTop ?? 0
      const left = viewport?.offsetLeft ?? 0
      const height = viewport?.height ?? window.innerHeight
      const width = viewport?.width ?? window.innerWidth
      const gap = 8
      const edge = 12
      const panelWidth = Math.min(280, width - edge * 2)
      const pageZoom = Number.parseFloat(window.getComputedStyle(document.body).zoom) || 1
      const below = top + height - anchor.bottom - gap - edge
      const above = anchor.top - top - gap - edge
      const placeAbove = below < 340 && above > below
      const available = Math.max(120, placeAbove ? above : below)
      const maxHeight = Math.min(380, available)
      setPosition({
        top: (placeAbove ? anchor.top - gap - maxHeight : anchor.bottom + gap) / pageZoom,
        left: Math.max(left + edge, Math.min(anchor.left, left + width - edge - panelWidth)) / pageZoom,
        width: panelWidth / pageZoom,
        maxHeight: maxHeight / pageZoom,
      })
    }
    updatePosition()
    popoverRef.current?.focus()
    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)
    window.visualViewport?.addEventListener('resize', updatePosition)
    window.visualViewport?.addEventListener('scroll', updatePosition)
    return () => {
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
      window.visualViewport?.removeEventListener('resize', updatePosition)
      window.visualViewport?.removeEventListener('scroll', updatePosition)
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    const onClickOutside = (e: MouseEvent) => {
      if (!containerRef.current?.contains(e.target as Node) && !popoverRef.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        setOpen(false)
        triggerRef.current?.focus()
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    window.addEventListener('keydown', onKey, true)
    return () => {
      document.removeEventListener('mousedown', onClickOutside)
      window.removeEventListener('keydown', onKey, true)
    }
  }, [open])

  const cells = buildMonthGrid(viewMonth)
  const minDay = startOfDay(min)
  const canGoPrevMonth =
    viewMonth.getFullYear() > min.getFullYear() ||
    (viewMonth.getFullYear() === min.getFullYear() && viewMonth.getMonth() > min.getMonth())

  const displayLabel = value
    ? value.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
    : 'Select date & time'

  const composedResult = (() => {
    if (!pendingDate) return null
    const [h, m] = pendingTime.split(':').map(Number)
    const result = new Date(pendingDate)
    result.setHours(h || 0, m || 0, 0, 0)
    return result
  })()

  const isTimeInvalid = composedResult ? composedResult < min : false

  const handleApply = () => {
    if (composedResult && !isTimeInvalid) {
      onChange(composedResult)
      setOpen(false)
      triggerRef.current?.focus()
    }
  }

  return (
    <div className="flex flex-col gap-1.5" ref={containerRef}>
      <label className="text-sm font-medium text-text-muted">{label}</label>
      <button
        ref={triggerRef}
        type="button"
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={() => {
          if (!open) {
            const base = value ?? min
            setViewMonth(new Date(base.getFullYear(), base.getMonth(), 1))
            setPendingDate(value ? startOfDay(value) : null)
            setPendingTime(value ? toTimeInputValue(value) : '09:00')
          }
          setOpen((o) => !o)
        }}
        className={cn(
          'w-full flex items-center gap-2 rounded-lg border border-border bg-surface',
          'px-3.5 py-2.5 text-sm text-left transition-colors',
          'hover:border-border-hover focus:outline-none focus:border-signal focus:ring-1 focus:ring-signal',
          value ? 'text-text-primary' : 'text-text-faint'
        )}
      >
        <CalendarIcon size={14} className="text-text-faint shrink-0" />
        {displayLabel}
      </button>

      {open && createPortal(
          <div
            ref={popoverRef}
            role="dialog"
            aria-label={`${label} date and time`}
            tabIndex={-1}
            onKeyDown={(event) => {
              if (event.key !== 'Tab') return
              const controls = Array.from(popoverRef.current?.querySelectorAll<HTMLButtonElement | HTMLInputElement>('button:not(:disabled), input:not(:disabled)') ?? [])
              if (!controls.length) return
              if (event.shiftKey && document.activeElement === controls[0]) {
                event.preventDefault()
                controls.at(-1)?.focus()
              } else if (!event.shiftKey && document.activeElement === controls.at(-1)) {
                event.preventDefault()
                controls[0].focus()
              }
            }}
            style={{ position: 'fixed', top: position.top, left: position.left, width: position.width, height: position.maxHeight }}
            className="z-[70] flex flex-col overflow-hidden rounded-xl border border-border bg-surface shadow-2xl p-3"
          >
            <div className="flex shrink-0 items-center justify-between mb-2">
              <button
                type="button"
                aria-label="Previous month"
                disabled={!canGoPrevMonth}
                onClick={() => setViewMonth(new Date(viewMonth.getFullYear(), viewMonth.getMonth() - 1, 1))}
                className="h-7 w-7 rounded-lg flex items-center justify-center text-text-muted hover:bg-surface-hover disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronLeft size={14} />
              </button>
              <span className="text-xs font-medium text-text-primary">
                {viewMonth.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}
              </span>
              <button
                type="button"
                aria-label="Next month"
                onClick={() => setViewMonth(new Date(viewMonth.getFullYear(), viewMonth.getMonth() + 1, 1))}
                className="h-7 w-7 rounded-lg flex items-center justify-center text-text-muted hover:bg-surface-hover"
              >
                <ChevronRight size={14} />
              </button>
            </div>

            <div className="grid shrink-0 grid-cols-7 gap-1 mb-1">
              {WEEKDAY_LABELS.map((d, i) => (
                <div key={i} className="h-5 flex items-center justify-center text-[10px] text-text-faint">
                  {d}
                </div>
              ))}
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto mb-2">
              <div className="grid grid-cols-7 gap-1">
                {cells.map((day, i) => {
                if (!day) return <div key={i} className="h-7" />
                const disabled = startOfDay(day) < minDay
                const isSelected = pendingDate && isSameDay(day, pendingDate)
                const isToday = isSameDay(day, new Date())
                return (
                  <button
                    key={i}
                    type="button"
                    disabled={disabled}
                    onClick={() => setPendingDate(startOfDay(day))}
                    className={cn(
                      'h-7 rounded-lg text-xs flex items-center justify-center transition-colors',
                      disabled && 'text-text-faint opacity-30 cursor-not-allowed',
                      !disabled && !isSelected && 'text-text-primary hover:bg-surface-hover',
                      isSelected && 'bg-signal text-void font-medium',
                      !isSelected && isToday && 'ring-1 ring-signal'
                    )}
                  >
                    {day.getDate()}
                  </button>
                )
                })}
              </div>
            </div>

              <div className="shrink-0 border-t border-border pt-3">
                <label className="text-[11px] text-text-faint mb-1.5 block">Time</label>
                <input
                  type="time"
                  value={pendingTime}
                  onChange={(e) => setPendingTime(e.target.value)}
                  className="w-full rounded-lg border border-border bg-surface-hover px-2.5 py-1.5 text-sm text-text-primary focus:outline-none focus:border-signal focus:ring-1 focus:ring-signal"
                />
                {isTimeInvalid && (
                  <p className="text-[10px] text-alert mt-1.5">
                    Must be in the future.
                  </p>
                )}
              </div>
            <div className="flex shrink-0 gap-2 bg-surface pt-2">
              <button type="button" onClick={() => { setOpen(false); triggerRef.current?.focus() }} className="flex-1 rounded-lg border border-border text-xs text-text-muted hover:text-text-primary">Cancel</button>
              <Button
                className="flex-1 min-h-10 bg-signal! text-void! shadow-md"
                disabled={!pendingDate || isTimeInvalid}
                onClick={handleApply}
              >
                Set
              </Button>
            </div>
          </div>
        , document.documentElement)}
    </div>
  )
}
