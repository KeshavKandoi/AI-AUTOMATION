import { Navigate, useLocation } from 'react-router-dom'

export default function ForgotPassword() {
  const location = useLocation()
  const email = (location.state as { email?: string } | null)?.email?.trim()

  return email
    ? <Navigate to="/reset-password" state={{ email, sendCode: true }} replace />
    : <Navigate to="/login" replace />
}
