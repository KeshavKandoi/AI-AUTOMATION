import { Link } from 'react-router-dom'
import BrandLogo from '@/components/BrandLogo'
import PillNav from '@/components/ui/PillNav'
import { LayoutDashboard } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'

export default function MarketingHeader() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  return (
    <header className="sticky top-0 z-20 border-b border-[var(--color-border)] bg-[var(--color-void)]/90 backdrop-blur-xl">
      <div className="mx-auto grid max-w-7xl grid-cols-[1fr_auto] items-center gap-x-4 gap-y-3 px-5 py-3.5 sm:px-8 md:grid-cols-[1fr_auto_1fr]">
        <BrandLogo size="lg" />
        <div className="col-span-2 row-start-2 min-w-0 justify-self-center md:col-span-1 md:col-start-2 md:row-auto"><PillNav /></div>
        {isAuthenticated ? (
          <Link to="/dashboard" className="col-start-2 row-start-1 inline-flex items-center justify-self-end gap-2 rounded-xl bg-[var(--color-signal)] px-4 py-2.5 text-sm font-semibold text-[var(--color-void)] transition hover:brightness-110 md:col-start-3 md:row-auto">
            <LayoutDashboard size={16} /> Workspace
          </Link>
        ) : (
          <div className="col-start-2 row-start-1 flex items-center justify-self-end gap-3 md:col-start-3 md:row-auto">
            <Link to="/login" className="hidden rounded-xl border border-[var(--color-signal)]/35 bg-[var(--color-signal-dim)] px-4 py-2.5 text-sm font-semibold text-[var(--color-signal)] transition hover:border-[var(--color-signal)]/60 hover:bg-[var(--color-signal)]/20 sm:inline">Sign in</Link>
            <Link to="/signup" className="rounded-xl bg-[var(--color-signal)] px-4 py-2.5 text-sm font-semibold text-[var(--color-void)] transition hover:brightness-110">Sign up</Link>
          </div>
        )}
      </div>
    </header>
  )
}
