import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
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
import GitHub from '@/pages/github/GitHub'
import Gmail from '@/pages/gmail/Gmail'

const queryClient = new QueryClient()

function App() {
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
              <Route path="/workflows" element={<ComingSoon title="Workflow Automations" />} />
              <Route path="/integrations/github" element={<GitHub />} />
              <Route path="/integrations/gmail" element={<Gmail />} />
              <Route path="/integrations/calendar" element={<ComingSoon title="Google Calendar" />} />
              <Route path="/commit-scheduler" element={<ComingSoon title="Commit Scheduler" />} />
              <Route path="/pull-requests" element={<ComingSoon title="Pull Requests" />} />
              <Route path="/approvals" element={<HumanApproval />} />
              <Route path="/audit-logs" element={<ComingSoon title="Audit Logs" />} />
              <Route path="/integrations" element={<Integrations />} />
              <Route path="/memory" element={<ComingSoon title="Memory" />} />
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
