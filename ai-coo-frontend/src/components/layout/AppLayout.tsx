import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import PageErrorBoundary from '@/components/ui/PageErrorBoundary'

export default function AppLayout() {
  const { pathname } = useLocation()
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <PageErrorBoundary key={pathname}>
          <Outlet />
        </PageErrorBoundary>
      </main>
    </div>
  )
}
