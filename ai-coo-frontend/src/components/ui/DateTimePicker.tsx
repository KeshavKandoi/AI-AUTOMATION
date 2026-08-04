import { useEffect, useRef, useState } from 'react'
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon, Clock } from 'lucide-react'
import { cn } from '@/lib/utils'

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

function generateTimeSlots(baseDate: Date, minDateTime: Date): { date: Date; label: string }[] {
  const slots: { date: Date; label: string }[] = []
  for (let h = 0; h < 24; h++) {
    for (let m = 0; m < 60; m += 30) {
      const slot = new Date(baseDate)
      slot.setHours(h, m, 0, 0)
      if (slot < minDateTime) continue
      const label = slot.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
      slots.push({ date: slot, label })
    }
  }
  return slots
}

export default function DateTimePicker({ label, value, onChange, minDate }: DateTimePickerProps) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const min = minDate ?? new Date()

  const [viewMonth, setViewMonth] = useState(() => {
    const base = value ?? min
    return new Date(base.getFullYear(), base.getMonth(), 1)
  })
  const [pendingDate, setPendingDate] = useState<Date | null>(value ? startOfDay(value) : null)

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  const cells = buildMonthGrid(viewMonth)
  const minDay = startOfDay(min)
  const canGoPrevMonth =
    viewMonth.getFullYear() > min.getFullYear() ||
    (viewMonth.getFullYear() === min.getFullYear() && viewMonth.getMonth() > min.getMonth())

  const activeDay = pendingDate ?? (value ? startOfDay(value) : null)
  const timeSlots = activeDay
    ? generateTimeSlots(activeDay, isSameDay(activeDay, new Date()) ? min : startOfDay(activeDay))
    : []

  const displayLabel = value
    ? value.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
    : 'Select date & time'

  return (
    <div className="flex flex-col gap-1.5" ref={containerRef}>
      <label className="text-sm font-medium text-[var(--color-text-muted)]">{label}</label>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={cn(
          'w-full flex items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]',
          'px-3.5 py-2.5 text-sm text-left transition-colors',
          'hover:border-[var(--color-border-hover)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)]',
          value ? 'text-[var(--color-text-primary)]' : 'text-[var(--color-text-faint)]'
        )}
      >
        <CalendarIcon size={14} className="text-[var(--color-text-faint)] shrink-0" />
        {displayLabel}
      </button>

      {open && (
        <div className="relative z-10">
          <div className="absolute top-1 left-0 w-[300px] rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-2xl p-3">
            <div className="flex items-center justify-between mb-2">
              <button
                type="button"
                disabled={!canGoPrevMonth}
                onClick={() => setViewMonth(new Date(viewMonth.getFullYear(), viewMonth.getMonth() - 1, 1))}
                className="h-7 w-7 rounded-lg flex items-center justify-center text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)] disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronLeft size={14} />
              </button>
              <span className="text-xs font-medium text-[var(--color-text-primary)]">
                {viewMonth.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}
              </span>
              <button
                type="button"
                onClick={() => setViewMonth(new Date(viewMonth.getFullYear(), viewMonth.getMonth() + 1, 1))}
                className="h-7 w-7 rounded-lg flex items-center justify-center text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)]"
              >
                <ChevronRight size={14} />
              </button>
            </div>

            <div className="grid grid-cols-7 gap-1 mb-1">
              {WEEKDAY_LABELS.map((d, i) => (
                <div key={i} className="h-6 flex items-center justify-center text-[10px] text-[var(--color-text-faint)]">
                  {d}
                </div>
              ))}
            </div>

            <div className="grid grid-cols-7 gap-1 mb-3">
              {cells.map((day, i) => {
                if (!day) return <div key={i} className="h-8" />
                const disabled = startOfDay(day) < minDay
                const isSelected = activeDay && isSameDay(day, activeDay)
                const isToday = isSameDay(day, new Date())
                return (
                  <button
                    key={i}
                    type="button"
                    disabled={disabled}
                    onClick={() => setPendingDate(startOfDay(day))}
                    className={cn(
                      'h-8 rounded-lg text-xs flex items-center justify-center transition-colors',
                      disabled && 'text-[var(--color-text-faint)] opacity-30 cursor-not-allowed',
                      !disabled && !isSelected && 'text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)]',
                      isSelected && 'bg-[var(--color-signal)] text-[var(--color-void)] font-medium',
                      !isSelected && isToday && 'ring-1 ring-[var(--color-signal)]'
                    )}
                  >
                    {day.getDate()}
                  </button>
                )
              })}
            </div>

            {activeDay && (
              <div>
                <div className="flex items-center gap-1.5 mb-2 text-[11px] text-[var(--color-text-faint)]">
                  <Clock size={11} />
                  Select a time
                </div>
                <div className="grid grid-cols-3 gap-1.5 max-h-36 overflow-y-auto pr-1">
                  {timeSlots.length === 0 ? (
                    <p className="col-span-3 text-[11px] text-[var(--color-text-faint)] py-2 text-center">
                      No times available today
                    </p>
                  ) : (
                    timeSlots.map((slot, i) => {
                      const isSelected = value && slot.date.getTime() === value.getTime()
                      return (
                        <button
                          key={i}
                          type="button"
                          onClick={() => {
                            onChange(slot.date)
                            setOpen(false)
                          }}
                          className={cn(
                            'rounded-lg px-2 py-1.5 text-[11px] transition-colors',
                            isSelected
                              ? 'bg-[var(--color-signal)] text-[var(--color-void)] font-medium'
                              : 'bg-[var(--color-surface-hover)] text-[var(--color-text-primary)] hover:brightness-110'
                          )}
                        >
                          {slot.label}
                        </button>
                      )
                    })
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
