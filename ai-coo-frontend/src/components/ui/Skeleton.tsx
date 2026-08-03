import { cn } from '@/lib/utils'

interface SkeletonProps {
  className?: string
}

export default function Skeleton({ className }: SkeletonProps) {
  return <div className={cn('rounded-lg bg-[var(--color-surface-hover)] animate-pulse', className)} />
}
