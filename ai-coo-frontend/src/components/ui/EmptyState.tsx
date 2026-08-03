import type { LucideIcon } from 'lucide-react'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  action?: React.ReactNode
}

export default function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-16 px-6">
      <div className="h-12 w-12 rounded-xl bg-[var(--color-surface-hover)] flex items-center justify-center mb-4">
        <Icon size={20} className="text-[var(--color-text-faint)]" />
      </div>
      <p className="text-sm text-[var(--color-text-primary)] font-medium mb-1">{title}</p>
      {description && <p className="text-xs text-[var(--color-text-faint)] max-w-sm mb-4">{description}</p>}
      {action}
    </div>
  )
}
