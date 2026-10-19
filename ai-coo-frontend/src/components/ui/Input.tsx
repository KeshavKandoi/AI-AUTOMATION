import { forwardRef, useState, type InputHTMLAttributes, type ReactNode } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { cn } from '@/lib/utils'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  leadingAdornment?: ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, leadingAdornment, type, className, id, ...props }, ref) => {
    const [showPassword, setShowPassword] = useState(false)
    const isPassword = type === 'password'
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-')

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="text-sm font-medium text-text-muted"
          >
            {label}
          </label>
        )}
        <div className="relative">
          {leadingAdornment && (
            <span aria-hidden="true" className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-lg leading-none">
              {leadingAdornment}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            type={isPassword ? (showPassword ? 'text' : 'password') : type}
            className={cn(
              'w-full rounded-lg border border-border bg-surface',
              'py-2.5 pl-3.5 pr-3.5 text-sm text-text-primary',
              'placeholder:text-text-faint',
              'transition-colors duration-150',
              'focus:outline-none focus:border-signal focus:ring-1 focus:ring-signal',
              'hover:border-border-hover',
              error && 'border-alert focus:border-alert focus:ring-alert',
              isPassword && 'pr-10',
              leadingAdornment && 'pl-12',
              className
            )}
            {...props}
          />
          {isPassword && (
            <button
              type="button"
              onClick={() => setShowPassword((s) => !s)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-text-faint hover:text-text-muted transition-colors"
              tabIndex={-1}
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          )}
        </div>
        {error && <span className="text-xs text-alert">{error}</span>}
      </div>
    )
  }
)
Input.displayName = 'Input'
