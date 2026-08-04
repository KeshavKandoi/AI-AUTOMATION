import { useEffect, useRef, useState } from 'react'
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
  const min = minDate ?? new Date()

  const [viewMonth, setViewMonth] = useState(() => {
    const base = value ?? min
    return new Date(base.getFullYear(), base.getMonth(), 1)
  })
  const [pendingDate, setPendingDate] = useState<Date | null>(value ? startOfDay(value) : null)
  const [pendingTime, setPendingTime] = useState<string>(value ? toTimeInputValue(value) : '09:00')

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
    }
  }

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
        <div className="relative z-20">
          <div className="absolute top-1 left-0 w-[280px] rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-2xl p-3 max-h-[380px] overflow-y-auto">
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
                const isSelected = pendingDate && isSameDay(day, pendingDate)
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

            {pendingDate && (
              <div className="border-t border-[var(--color-border)] pt-3">
                <label className="text-[11px] text-[var(--color-text-faint)] mb-1.5 block">Time</label>
                <input
                  type="time"
                  value={pendingTime}
                  onChange={(e) => setPendingTime(e.target.value)}
                  className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-hover)] px-2.5 py-1.5 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)]"
                />
                {isTimeInvalid && (
                  <p className="text-[10px] text-[var(--color-alert)] mt-1.5">
                    Must be in the future.
                  </p>
                )}
                <Button
                  className="w-full mt-2"
                  disabled={isTimeInvalid}
                  onClick={handleApply}
                >
                  Set
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
