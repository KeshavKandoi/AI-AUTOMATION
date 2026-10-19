import { Outlet, useLocation } from 'react-router-dom'
import { Suspense } from 'react'
import Sidebar from './Sidebar'
import PageErrorBoundary from '@/components/ui/PageErrorBoundary'

export default function AppLayout() {
  const { pathname } = useLocation()
  return (
    <div className={`flex h-screen overflow-hidden ${pathname === '/dashboard' ? 'dashboard-theme' : ''}`}>
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <PageErrorBoundary key={pathname}>
          <Suspense fallback={<div className="p-6 text-sm text-[var(--color-text-muted)]">Loading page…</div>}>
            <Outlet />
          </Suspense>
        </PageErrorBoundary>
      </main>
    </div>
  )
}
