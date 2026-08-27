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
import JobHunter from '@/pages/jobHunter/JobHunter'
import Integrations from '@/pages/integrations/Integrations'
import CommitScheduler from '@/pages/commitScheduler/CommitScheduler'
import PullRequests from '@/pages/pullRequests/PullRequests'
import OpenSource from '@/pages/openSource/OpenSource'
import GitHub from '@/pages/github/GitHub'
import Gmail from '@/pages/gmail/Gmail'
import CalendarPage from '@/pages/calendar/Calendar'
import Workflows from '@/pages/workflows/Workflows'
import AuditLogs from '@/pages/auditLogs/AuditLogs'
import Settings from '@/pages/settings/Settings'
import Memory from '@/pages/memory/Memory'
import Notifications from '@/pages/notifications/Notifications'
import Analytics from '@/pages/analytics/Analytics'
import Home from '@/pages/home/Home'
import PrivacyPolicy from '@/pages/legal/PrivacyPolicy'
import TermsOfService from '@/pages/legal/TermsOfService'
import Security from '@/pages/legal/Security'

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
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/verify-otp" element={<VerifyOtp />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/privacy" element={<PrivacyPolicy />} />
          <Route path="/terms" element={<TermsOfService />} />
          <Route path="/security" element={<Security />} />

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
              <Route path="/pull-requests" element={<PullRequests />} />
              <Route path="/open-source" element={<OpenSource />} />
              <Route path="/approvals" element={<HumanApproval />} />
              <Route path="/job-hunter" element={<JobHunter />} />
              <Route path="/audit-logs" element={<AuditLogs />} />
              <Route path="/integrations" element={<Integrations />} />
              <Route path="/memory" element={<Memory />} />
              <Route path="/notifications" element={<Notifications />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/settings" element={<Settings />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
