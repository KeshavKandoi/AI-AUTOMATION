import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { useAuthStore } from '@/store/authStore'
import Login from '@/pages/auth/Login'
import Signup from '@/pages/auth/Signup'
import VerifyOtp from '@/pages/auth/VerifyOtp'
import ForgotPassword from '@/pages/auth/ForgotPassword'
import ResetPassword from '@/pages/auth/ResetPassword'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import AppLayout from '@/components/layout/AppLayout'
import Dashboard from '@/pages/dashboard/Dashboard'
import ComingSoon from '@/pages/ComingSoon'
import Tasks from '@/pages/tasks/Tasks'
import HumanApproval from '@/pages/approvals/HumanApproval'
import Integrations from '@/pages/integrations/Integrations'
import CommitScheduler from '@/pages/commitScheduler/CommitScheduler'
import GitHub from '@/pages/github/GitHub'
import Gmail from '@/pages/gmail/Gmail'
import CalendarPage from '@/pages/calendar/Calendar'
import Workflows from '@/pages/workflows/Workflows'
import AuditLogs from '@/pages/auditLogs/AuditLogs'
import Memory from '@/pages/memory/Memory'

const queryClient = new QueryClient()

function App() {
  const [bootstrapped, setBootstrapped] = useState(false)
  const isDevAccount = useAuthStore((s) => s.isDevAccount)
  const setAuth = useAuthStore((s) => s.setAuth)
  const logout = useAuthStore((s) => s.logout)

  useEffect(() => {
    // Dev Account has no real session/refresh cookie — skip the silent
    // refresh attempt entirely and just render immediately.
    if (isDevAccount) {
      setBootstrapped(true)
      return
    }
    apiClient
      .post('/auth/refresh')
      .then((res) => setAuth(res.data.user, res.data.access_token))
      .catch(() => logout())
      .finally(() => setBootstrapped(true))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (!bootstrapped) return null

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/verify-otp" element={<VerifyOtp />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/chat" element={<ComingSoon title="AI COO Chat" />} />
              <Route path="/tasks" element={<Tasks />} />
              <Route path="/workflows" element={<Workflows />} />
              <Route path="/integrations/github" element={<GitHub />} />
              <Route path="/integrations/gmail" element={<Gmail />} />
              <Route path="/integrations/calendar" element={<CalendarPage />} />
              <Route path="/commit-scheduler" element={<CommitScheduler />} />
              <Route path="/pull-requests" element={<ComingSoon title="Pull Requests" />} />
              <Route path="/approvals" element={<HumanApproval />} />
              <Route path="/audit-logs" element={<AuditLogs />} />
              <Route path="/integrations" element={<Integrations />} />
              <Route path="/memory" element={<Memory />} />
              <Route path="/notifications" element={<ComingSoon title="Notifications" />} />
              <Route path="/analytics" element={<ComingSoon title="Analytics" />} />
              <Route path="/settings" element={<ComingSoon title="Settings" />} />
              <Route path="/profile" element={<ComingSoon title="Profile" />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
