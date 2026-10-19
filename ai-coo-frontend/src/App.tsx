import { useEffect, useRef, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { isPublicPath, restoreSession } from '@/api/client'
import { useAuthStore } from '@/store/authStore'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import AppLayout from '@/components/layout/AppLayout'
import PageErrorBoundary from '@/components/ui/PageErrorBoundary'
import Home from '@/pages/home/Home'
import { FeaturesPage, HowItWorksPage, ConnectionsPage, GoogleDataPage } from '@/pages/home/MarketingPages'
import Memory from '@/pages/memory/Memory'
import CalendarPage from '@/pages/calendar/Calendar'
import Login from '@/pages/auth/Login'
import Signup from '@/pages/auth/Signup'
import VerifyOtp from '@/pages/auth/VerifyOtp'
import ForgotPassword from '@/pages/auth/ForgotPassword'
import ResetPassword from '@/pages/auth/ResetPassword'
import Dashboard from '@/pages/dashboard/Dashboard'
import Tasks from '@/pages/tasks/Tasks'
import JobHunter from '@/pages/jobHunter/JobHunter'
import Integrations from '@/pages/integrations/Integrations'
import CommitScheduler from '@/pages/commitScheduler/CommitScheduler'
import PullRequests from '@/pages/pullRequests/PullRequests'
import OpenSource from '@/pages/openSource/OpenSource'
import GitHub from '@/pages/github/GitHub'
import Workflows from '@/pages/workflows/Workflows'
import AuditLogs from '@/pages/auditLogs/AuditLogs'
import Settings from '@/pages/settings/Settings'
import Notifications from '@/pages/notifications/Notifications'
import Analytics from '@/pages/analytics/Analytics'
import PrivacyPolicy from '@/pages/legal/PrivacyPolicy'
import TermsOfService from '@/pages/legal/TermsOfService'
import Security from '@/pages/legal/Security'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, refetchOnWindowFocus: false },
  },
})

function App() {
  const [checkingUncachedSession, setCheckingUncachedSession] = useState(
    () => !isPublicPath(window.location.pathname) && !useAuthStore.getState().user
  )
  const restoreOnMount = useRef(!!useAuthStore.getState().user || checkingUncachedSession)

  useEffect(() => {
    if (restoreOnMount.current) {
      void restoreSession().finally(() => setCheckingUncachedSession(false))
    }
  }, [])

  if (checkingUncachedSession) {
    return <div className="min-h-screen bg-void p-8 text-sm text-text-muted">Restoring your session…</div>
  }

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/features" element={<FeaturesPage />} />
          <Route path="/how-it-works" element={<HowItWorksPage />} />
          <Route path="/connections" element={<ConnectionsPage />} />
          <Route path="/google-data" element={<GoogleDataPage />} />
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
              <Route path="/tasks" element={<Tasks />} />
              <Route path="/workflows" element={<Workflows />} />
              <Route path="/integrations/github" element={<GitHub />} />
              <Route path="/integrations/calendar" element={<CalendarPage />} />
              <Route path="/commit-scheduler" element={<PageErrorBoundary><CommitScheduler /></PageErrorBoundary>} />
              <Route path="/pull-requests" element={<PullRequests />} />
              <Route path="/open-source" element={<OpenSource />} />
              <Route path="/approvals" element={<Navigate to="/tasks" replace />} />
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
