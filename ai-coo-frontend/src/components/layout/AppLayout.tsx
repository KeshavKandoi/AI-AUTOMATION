import { Outlet, useLocation } from 'react-router-dom'
import { Suspense } from 'react'
import Sidebar from './Sidebar'
import PageErrorBoundary from '@/components/ui/PageErrorBoundary'
import PageLoading from '@/components/ui/PageLoading'

export default function AppLayout() {
  const { pathname } = useLocation()
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <PageErrorBoundary key={pathname}>
          <Suspense fallback={<PageLoading />}>
            <Outlet />
          </Suspense>
        </PageErrorBoundary>
      </main>
    </div>
  )
}
