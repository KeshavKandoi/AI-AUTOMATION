import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'

interface BrandLogoProps {
  className?: string
  compact?: boolean
  size?: 'sm' | 'md' | 'lg'
  to?: string
}

const MARK_SIZE = {
  sm: 'h-7 w-[72px]',
  md: 'h-9 w-[93px]',
  lg: 'h-10 w-[104px]',
}

export default function BrandLogo({ className, compact = false, size = 'md', to = '/' }: BrandLogoProps) {
  return (
    <Link to={to} className={cn('inline-flex min-w-0 items-center gap-2.5', className)} aria-label="WorkForge home">
      <img
        src={compact ? '/workforge-icon.svg' : '/workforge-mark.svg'}
        alt=""
        className={compact ? 'h-8 w-8 shrink-0' : cn('shrink-0 object-contain', MARK_SIZE[size])}
      />
      {!compact && <span className="truncate font-[family-name:var(--font-display)] text-lg font-semibold tracking-tight text-[var(--color-text-primary)]">WorkForge</span>}
    </Link>
  )
}
