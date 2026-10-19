import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

export default function ProtectedRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const cachedUser = useAuthStore((s) => s.user)
  if (!isAuthenticated && !cachedUser) return <Navigate to="/" replace />
  return <Outlet />
}
