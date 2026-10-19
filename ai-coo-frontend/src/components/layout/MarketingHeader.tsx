import { Link } from 'react-router-dom'
import BrandLogo from '@/components/BrandLogo'
import PillNav from '@/components/ui/PillNav'
import { LayoutDashboard } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'

export default function MarketingHeader() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-void/90 backdrop-blur-xl">
      <div className="mx-auto grid max-w-7xl grid-cols-[1fr_auto] items-center gap-x-4 gap-y-3 px-5 py-3.5 sm:px-8 md:grid-cols-[1fr_auto_1fr]">
        <BrandLogo compact className="sm:hidden" />
        <BrandLogo size="lg" className="hidden sm:inline-flex" />
        <div className="col-span-2 row-start-2 min-w-0 justify-self-center md:col-span-1 md:col-start-2 md:row-auto"><PillNav /></div>
        {isAuthenticated ? (
          <Link to="/dashboard" className="col-start-2 row-start-1 inline-flex items-center justify-self-end gap-2 rounded-xl bg-signal px-4 py-2.5 text-sm font-semibold text-void transition hover:brightness-110 md:col-start-3 md:row-auto">
            <LayoutDashboard size={16} /> Workspace
          </Link>
        ) : (
          <div className="col-start-2 row-start-1 flex items-center justify-self-end gap-3 md:col-start-3 md:row-auto">
            <Link to="/login" className="rounded-xl border border-signal/35 bg-signal-dim px-3 py-2.5 text-sm font-semibold text-signal transition hover:border-signal/60 hover:bg-signal/20 sm:px-4">Sign in</Link>
            <Link to="/signup" className="rounded-xl bg-signal px-4 py-2.5 text-sm font-semibold text-void transition hover:brightness-110">Sign up</Link>
          </div>
        )}
      </div>
    </header>
  )
}
