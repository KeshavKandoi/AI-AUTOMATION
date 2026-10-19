import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { isPublicPath, restoreSession } from '@/api/client'
import { useAuthStore } from '@/store/authStore'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import AppLayout from '@/components/layout/AppLayout'
import PageErrorBoundary from '@/components/ui/PageErrorBoundary'
const Home = lazy(() => import('@/pages/home/Home'))
const FeaturesPage = lazy(() => import('@/pages/home/MarketingPages').then((module) => ({ default: module.FeaturesPage })))
const HowItWorksPage = lazy(() => import('@/pages/home/MarketingPages').then((module) => ({ default: module.HowItWorksPage })))
const ConnectionsPage = lazy(() => import('@/pages/home/MarketingPages').then((module) => ({ default: module.ConnectionsPage })))
const GoogleDataPage = lazy(() => import('@/pages/home/MarketingPages').then((module) => ({ default: module.GoogleDataPage })))
const Memory = lazy(() => import('@/pages/memory/Memory'))
const CalendarPage = lazy(() => import('@/pages/calendar/Calendar'))
const Login = lazy(() => import('@/pages/auth/Login'))
const Signup = lazy(() => import('@/pages/auth/Signup'))

const VerifyOtp = lazy(() => import('@/pages/auth/VerifyOtp'))
const ForgotPassword = lazy(() => import('@/pages/auth/ForgotPassword'))
const ResetPassword = lazy(() => import('@/pages/auth/ResetPassword'))
const Dashboard = lazy(() => import('@/pages/dashboard/Dashboard'))
const Tasks = lazy(() => import('@/pages/tasks/Tasks'))
const JobHunter = lazy(() => import('@/pages/jobHunter/JobHunter'))
const Integrations = lazy(() => import('@/pages/integrations/Integrations'))
const CommitScheduler = lazy(() => import('@/pages/commitScheduler/CommitScheduler'))
const PullRequests = lazy(() => import('@/pages/pullRequests/PullRequests'))
const OpenSource = lazy(() => import('@/pages/openSource/OpenSource'))
const GitHub = lazy(() => import('@/pages/github/GitHub'))
const Workflows = lazy(() => import('@/pages/workflows/Workflows'))
const AuditLogs = lazy(() => import('@/pages/auditLogs/AuditLogs'))
const Settings = lazy(() => import('@/pages/settings/Settings'))
const Notifications = lazy(() => import('@/pages/notifications/Notifications'))
const Analytics = lazy(() => import('@/pages/analytics/Analytics'))
const PrivacyPolicy = lazy(() => import('@/pages/legal/PrivacyPolicy'))
const TermsOfService = lazy(() => import('@/pages/legal/TermsOfService'))
const Security = lazy(() => import('@/pages/legal/Security'))

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
    return <div className="min-h-screen bg-[var(--color-void)] p-8 text-sm text-[var(--color-text-muted)]">Restoring your session…</div>
  }

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={<div className="min-h-screen bg-[var(--color-void)] p-8 text-sm text-[var(--color-text-muted)]">Loading page…</div>}>
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
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
