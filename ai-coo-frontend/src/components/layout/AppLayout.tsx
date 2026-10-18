import { Outlet } from 'react-router-dom'
import { Suspense } from 'react'
import Sidebar from './Sidebar'

export default function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <Suspense fallback={<div className="p-6 text-sm text-[var(--color-text-muted)]">Loading page…</div>}>
          <Outlet />
        </Suspense>
      </main>
    </div>
  )
}
