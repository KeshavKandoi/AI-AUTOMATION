import { useState, type KeyboardEvent } from 'react'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'

interface TagInputProps {
  label?: string
  value: string[]
  onChange: (tags: string[]) => void
  placeholder?: string
  error?: string
}

// Reusable chip/tag input — type + Enter (or comma) to add, click x to
// remove. Used for free-text multi-value fields like desired roles,
// skills, and preferred locations.
export default function TagInput({ label, value, onChange, placeholder, error }: TagInputProps) {
  const [draft, setDraft] = useState('')

  function commitDraft() {
    const trimmed = draft.trim()
    if (trimmed && !value.includes(trimmed)) {
      onChange([...value, trimmed])
    }
    setDraft('')
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      commitDraft()
    } else if (e.key === 'Backspace' && !draft && value.length > 0) {
      onChange(value.slice(0, -1))
    }
  }

  function removeTag(tag: string) {
    onChange(value.filter((t) => t !== tag))
  }

  return (
    <div className="flex flex-col gap-1.5">
      {label && <label className="text-sm font-medium text-[var(--color-text-muted)]">{label}</label>}
      <div
        className={cn(
          'flex flex-wrap gap-1.5 items-center rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]',
          'px-2.5 py-2 min-h-[42px] transition-colors',
          'focus-within:border-[var(--color-signal)] focus-within:ring-1 focus-within:ring-[var(--color-signal)]',
          'hover:border-[var(--color-border-hover)]',
          error && 'border-[var(--color-alert)]'
        )}
      >
        {value.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-md bg-[var(--color-surface-hover)] pl-2 pr-1 py-1 text-xs text-[var(--color-text-primary)]"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(tag)}
              className="text-[var(--color-text-faint)] hover:text-[var(--color-alert)] transition-colors"
            >
              <X size={11} />
            </button>
          </span>
        ))}
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={commitDraft}
          placeholder={value.length === 0 ? placeholder : ''}
          className="flex-1 min-w-[100px] bg-transparent text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-faint)] focus:outline-none py-0.5"
        />
      </div>
      {error && <span className="text-xs text-[var(--color-alert)]">{error}</span>}
    </div>
  )
}
