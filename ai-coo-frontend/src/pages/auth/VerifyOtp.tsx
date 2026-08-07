import { useState, useRef, useEffect } from 'react'
import { useLocation, useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/Button'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/store/authStore'

export default function VerifyOtp() {
  const navigate = useNavigate()
  const location = useLocation()
  const setAuth = useAuthStore((s) => s.setAuth)
  const email = (location.state as { email?: string })?.email ?? ''

  const [digits, setDigits] = useState<string[]>(Array(6).fill(''))
  const [serverError, setServerError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [cooldown, setCooldown] = useState(0)
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
    if (cooldown > 0) return
    try {
      await authApi.resendOtp(email)
      setCooldown(30)
    } catch (err: any) {
      setServerError(err?.response?.data?.detail ?? 'Could not resend the code.')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden">
      <div className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 h-96 w-96 rounded-full bg-[var(--color-signal)] opacity-[0.06] blur-[120px]" />

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="w-full max-w-sm relative"
      >
        <div className="mb-8 text-center">
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
            Check your email
          </h1>
          <p className="mt-1.5 text-sm text-[var(--color-text-muted)]">
            Enter the 6-digit code we sent to{' '}
            <span className="text-[var(--color-text-primary)] font-mono">{email || 'your email'}</span>
          </p>
        </div>

        <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60 backdrop-blur-xl p-6 flex flex-col gap-5">
          {serverError && (
            <div className="rounded-lg bg-[var(--color-alert-dim)] border border-[var(--color-alert)]/30 px-3 py-2 text-xs text-[var(--color-alert)]">
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
                className="w-11 h-12 text-center rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] text-lg font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)] transition-colors"
              />
            ))}
          </div>

          <Button onClick={handleVerify} loading={loading} disabled={otp.length !== 6} className="w-full">
            Verify email
          </Button>

          <button
            type="button"
            onClick={handleResend}
            disabled={cooldown > 0}
            className="text-sm text-[var(--color-signal)] hover:brightness-110 transition-all disabled:text-[var(--color-text-faint)] disabled:cursor-not-allowed"
          >
            {cooldown > 0 ? `Resend code in ${cooldown}s` : 'Resend code'}
          </button>
        </div>

        <p className="mt-6 text-center text-sm text-[var(--color-text-muted)]">
          Wrong email?{' '}
          <Link to="/signup" className="text-[var(--color-signal)] hover:brightness-110 transition-all">
            Go back
          </Link>
        </p>
      </motion.div>
    </div>
  )
}
