import { useState, useRef, useEffect } from 'react'
import { useLocation, useNavigate, Link, Navigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/Button'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/store/authStore'
import BrandLogo from '@/components/BrandLogo'

export default function VerifyOtp() {
  const navigate = useNavigate()
  const location = useLocation()
  const setAuth = useAuthStore((s) => s.setAuth)
  const email = (location.state as { email?: string })?.email ?? ''

  const [digits, setDigits] = useState<string[]>(Array(6).fill(''))
  const [serverError, setServerError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [cooldown, setCooldown] = useState(0)
  const [resendLoading, setResendLoading] = useState(false)
  const [resendStatus, setResendStatus] = useState<string | null>(null)
  const inputsRef = useRef<(HTMLInputElement | null)[]>([])

  useEffect(() => {
    if (cooldown <= 0) return
    const t = setInterval(() => setCooldown((c) => c - 1), 1000)
    return () => clearInterval(t)
  }, [cooldown])

  const handleChange = (index: number, value: string) => {
    if (!/^[0-9]?$/.test(value)) return
    const next = [...digits]
    next[index] = value
    setDigits(next)
    if (value && index < 5) inputsRef.current[index + 1]?.focus()
  }

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputsRef.current[index - 1]?.focus()
    }
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
    if (!pasted) return
    e.preventDefault()
    setDigits(pasted.padEnd(6, ' ').split('').map((c) => (c === ' ' ? '' : c)))
    inputsRef.current[Math.min(pasted.length, 5)]?.focus()
  }

  const otp = digits.join('')

  const handleVerify = async () => {
    if (otp.length !== 6) return
    setServerError(null)
    setLoading(true)
    try {
      const res = await authApi.verifyOtp({ email, otp })
      setAuth(res.data.user, res.data.access_token)
      navigate('/dashboard')
    } catch (err: any) {
      setServerError(err?.response?.data?.detail ?? 'Invalid or expired code. Try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleResend = async () => {
    if (cooldown > 0 || resendLoading) return
    setServerError(null)
    setResendStatus(null)
    setResendLoading(true)
    try {
      await authApi.resendOtp(email)
      setCooldown(30)
      setResendStatus('If this address still needs verification, check your inbox for a recent code.')
    } catch (err: any) {
      setServerError(err?.response?.data?.detail ?? 'Could not resend the code.')
    } finally {
      setResendLoading(false)
    }
  }

  if (!email) return <Navigate to="/signup" replace />

  return (
    <div className="reset-otp-page min-h-screen flex items-center justify-center bg-void px-4 relative overflow-hidden">
      <div className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 h-96 w-96 rounded-full bg-signal opacity-[0.06] blur-[120px]" />

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="w-full max-w-sm relative"
      >
        <div className="mb-8 text-center"><BrandLogo size="md" /></div>
        <div className="mb-8 text-center">
          <h1 className="font-display text-2xl font-semibold text-text-primary">
            Verify your email
          </h1>
          <p className="mt-1.5 text-sm text-text-muted">
            Enter the 6-digit code for{' '}
            <span className="text-text-primary font-mono">{email || 'your email'}</span>
          </p>
        </div>

        <div className="rounded-2xl border border-signal/25 bg-surface/80 backdrop-blur-xl p-6 flex flex-col gap-5">
          {serverError && (
            <div className="rounded-lg bg-alert-dim border border-alert/30 px-3 py-2 text-xs text-alert">
              {serverError}
            </div>
          )}

          <div className="flex justify-between gap-2" onPaste={handlePaste}>
            {digits.map((digit, i) => (
              <input
                key={i}
                ref={(el) => { inputsRef.current[i] = el }}
                value={digit}
                onChange={(e) => handleChange(i, e.target.value)}
                onKeyDown={(e) => handleKeyDown(i, e)}
                maxLength={1}
                inputMode="numeric"
                aria-label={`Verification code digit ${i + 1}`}
                className="w-11 h-12 text-center rounded-lg border border-signal/25 bg-surface text-lg font-mono text-text-primary focus:outline-none focus:border-signal focus:ring-1 focus:ring-signal transition-colors"
              />
            ))}
          </div>

          <Button onClick={handleVerify} loading={loading} disabled={otp.length !== 6} className="w-full text-white">
            Verify email
          </Button>

          <button
            type="button"
            onClick={handleResend}
            disabled={cooldown > 0 || resendLoading}
            className="text-sm text-[#e88cab] hover:brightness-110 transition-all disabled:text-text-faint disabled:cursor-not-allowed"
          >
            {resendLoading ? 'Checking…' : cooldown > 0 ? `Resend code in ${cooldown}s` : 'Resend code'}
          </button>
          {resendStatus && <p role="status" className="text-center text-xs text-text-muted">{resendStatus}</p>}
        </div>

        <p className="mt-6 text-center text-sm text-text-muted">
          Already verified?{' '}
          <Link to="/login" className="text-[#e88cab] hover:brightness-110 transition-all">Sign in</Link>
          <span className="mx-2 text-text-faint">·</span>
          <Link to="/signup" className="text-[#e88cab] hover:brightness-110 transition-all">
            Change email
          </Link>
        </p>
      </motion.div>
    </div>
  )
}
