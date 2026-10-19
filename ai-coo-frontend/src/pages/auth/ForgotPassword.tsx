import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { authApi } from '@/api/auth'
import AuthShell from './AuthShell'

export default function ForgotPassword() {
  const navigate = useNavigate()
  const location = useLocation()
  const email = (location.state as { email?: string } | null)?.email?.trim() ?? ''
  const [error, setError] = useState<string | null>(null)
  const [sending, setSending] = useState(true)
  const requestedEmail = useRef<string | null>(null)

  const sendCode = useCallback(async () => {
    if (!email) return
    setSending(true)
    setError(null)
    try {
      await authApi.forgotPassword({ email })
      navigate('/reset-password', { state: { email }, replace: true })
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Could not send the reset code. Please try again.')
      setSending(false)
    }
  }, [email, navigate])

  useEffect(() => {
    if (!email || requestedEmail.current === email) return
    requestedEmail.current = email
    void sendCode()
  }, [email, sendCode])

  if (!email) return <Navigate to="/login" replace />

  return (
    <AuthShell>
      <div className="mb-8">
        <h1 className="font-display text-3xl font-semibold tracking-tight text-text-primary sm:text-4xl">Reset your password</h1>
        <p className="mt-3 text-sm leading-6 text-text-muted">We’ll send a reset code to the email you entered on the sign-in page.</p>
      </div>

      <div className="rounded-[1.75rem] border border-border bg-surface/75 p-7 shadow-xl shadow-black/10 sm:p-10">
        {error ? (
          <div role="alert" className="flex flex-col gap-5">
            <p className="rounded-lg border border-alert/30 bg-alert-dim px-4 py-3 text-sm text-alert">{error}</p>
            <Button type="button" onClick={() => void sendCode()} loading={sending} className="h-14 w-full rounded-xl">Try again</Button>
          </div>
        ) : (
          <p aria-live="polite" className="text-sm text-text-muted">
            Sending a reset code to <span className="font-medium text-text-primary">{email}</span>…
          </p>
        )}
      </div>

      <p className="mt-7 text-center text-sm text-text-muted">
        <Link to="/login" className="font-semibold text-signal hover:brightness-110 transition-all">Back to sign in</Link>
      </p>
    </AuthShell>
  )
}
