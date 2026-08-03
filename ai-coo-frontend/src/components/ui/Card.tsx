import { cn } from '@/lib/utils'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

export default function Card({ children, className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60 backdrop-blur-xl',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}
