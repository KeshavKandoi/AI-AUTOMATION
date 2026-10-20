import { useState, useRef, useEffect, useCallback } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { authApi } from '@/api/auth'
import BrandLogo from '@/components/BrandLogo'

const schema = z.object({
  otp: z.string().length(6, 'Enter the 6-digit code'),
  new_password: z.string().min(8, 'At least 8 characters'),
})
type ResetForm = z.infer<typeof schema>

export default function ResetPassword() {
  const navigate = useNavigate()
  const location = useLocation()
  const resetState = location.state as { email?: string; sendCode?: boolean } | null
  const email = resetState?.email?.trim() ?? ''
  const shouldSendCode = Boolean(resetState?.sendCode)

  const [serverError, setServerError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)
  const [cooldown, setCooldown] = useState(0)
  const [resendError, setResendError] = useState<string | null>(null)
  const [codeRequestError, setCodeRequestError] = useState<string | null>(null)
  const [sendingCode, setSendingCode] = useState(shouldSendCode)
  const [digits, setDigits] = useState<string[]>(Array(6).fill(''))
  const inputsRef = useRef<(HTMLInputElement | null)[]>([])
  const requestedEmail = useRef<string | null>(null)

  const {
    handleSubmit,
    control,
    register,
    setValue,
    formState: { errors },
  } = useForm<ResetForm>({ resolver: zodResolver(schema), defaultValues: { otp: '' } })

  const sendResetCode = useCallback(async () => {
    if (!email) return
    setSendingCode(true)
    setCodeRequestError(null)
    try {
      await authApi.forgotPassword({ email })
      setCooldown(30)
      navigate('/reset-password', { state: { email }, replace: true })
    } catch (err: any) {
      setCodeRequestError(err?.response?.data?.detail ?? 'Could not send the reset code. Please try again.')
    } finally {
      setSendingCode(false)
    }
  }, [email, navigate])

  useEffect(() => {
    if (!shouldSendCode || !email || requestedEmail.current === email) return
    requestedEmail.current = email
    void sendResetCode()
  }, [email, sendResetCode, shouldSendCode])

  useEffect(() => {
    if (cooldown <= 0) return
    const t = setInterval(() => setCooldown((c) => c - 1), 1000)
    return () => clearInterval(t)
  }, [cooldown])

  const handleDigitChange = (index: number, value: string) => {
    if (!/^[0-9]?$/.test(value)) return
    const next = [...digits]
    next[index] = value
    setDigits(next)
    setValue('otp', next.join(''), { shouldValidate: true })
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
    const next = pasted.padEnd(6, ' ').split('').map((c) => (c === ' ' ? '' : c))
    setDigits(next)
    setValue('otp', next.join(''), { shouldValidate: true })
    inputsRef.current[Math.min(pasted.length, 5)]?.focus()
  }

  const handleResend = async () => {
    if (cooldown > 0 || sendingCode || codeRequestError) return
    setResendError(null)
    try {
      await authApi.resendResetOtp(email)
      setCooldown(30)
    } catch (err: any) {
      setResendError(err?.response?.data?.detail ?? 'Could not resend the code.')
    }
  }

  const onSubmit = async (data: ResetForm) => {
    setServerError(null)
    setLoading(true)
    try {
      await authApi.resetPassword({ email, ...data })
      setSuccess(true)
      setTimeout(() => navigate('/login'), 1800)
    } catch (err: any) {
      setServerError(err?.response?.data?.detail ?? 'Could not reset password. Check the code.')
    } finally {
      setLoading(false)
    }
  }

  if (!email) return <Navigate to="/login" replace />

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
            Set a new password
          </h1>
          <p className="mt-1.5 text-sm text-text-muted">
            Enter the code sent to{' '}
            <span className="text-text-primary font-mono">{email || 'your email'}</span>
          </p>
        </div>

        {success ? (
          <div className="rounded-2xl border border-signal/30 bg-signal-dim p-6 text-center">
            <p className="text-sm text-signal">
              Password reset. Taking you to sign in…
            </p>
          </div>
        ) : (
          <form
            onSubmit={handleSubmit(onSubmit)}
            className="rounded-2xl border border-signal/25 bg-surface/80 backdrop-blur-xl p-6 flex flex-col gap-5"
          >
            {sendingCode && <p role="status" className="text-sm text-text-muted">Sending a reset code to {email}…</p>}
            {codeRequestError && (
              <div role="alert" className="rounded-lg bg-alert-dim border border-alert/30 px-3 py-2 text-sm text-alert">
                <p>{codeRequestError}</p>
                <button type="button" onClick={() => void sendResetCode()} className="mt-2 font-semibold text-[#e88cab] hover:brightness-110">Try sending again</button>
              </div>
            )}
            {serverError && (
              <div className="rounded-lg bg-alert-dim border border-alert/30 px-3 py-2 text-xs text-alert">
                {serverError}
              </div>
            )}

            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-text-muted">Reset code</label>
              <div className="flex justify-between gap-2" onPaste={handlePaste}>
                {digits.map((digit, i) => (
                  <input
                    key={i}
                    ref={(el) => { inputsRef.current[i] = el }}
                    value={digit}
                    onChange={(e) => handleDigitChange(i, e.target.value)}
                    onKeyDown={(e) => handleKeyDown(i, e)}
                    maxLength={1}
                    inputMode="numeric"
                    aria-label={`Reset code digit ${i + 1}`}
                    className="w-11 h-12 text-center rounded-lg border border-signal/25 bg-surface text-lg font-mono text-text-primary focus:outline-none focus:border-signal focus:ring-1 focus:ring-signal transition-colors"
                  />
                ))}
              </div>
              <Controller name="otp" control={control} render={() => <></>} />
              {errors.otp && (
                <p className="text-xs text-alert">{errors.otp.message}</p>
              )}
              <button
                type="button"
                onClick={handleResend}
                disabled={cooldown > 0 || sendingCode || Boolean(codeRequestError)}
                className="self-start text-xs text-[#e88cab] hover:brightness-110 transition-all disabled:text-text-faint disabled:cursor-not-allowed"
              >
                {sendingCode ? 'Sending code…' : cooldown > 0 ? `Resend code in ${cooldown}s` : 'Resend code'}
              </button>
              {resendError && (
                <p className="text-xs text-alert">{resendError}</p>
              )}
            </div>

            <Input
              label="New password"
              type="password"
              placeholder="At least 8 characters"
              autoComplete="new-password"
              error={errors.new_password?.message}
              {...register('new_password')}
            />

            <Button type="submit" loading={loading} disabled={sendingCode || Boolean(codeRequestError)} className="w-full mt-1 text-white">
              Reset password
            </Button>
          </form>
        )}

        <p className="mt-6 text-center text-sm text-text-muted">
          <Link to="/login" className="text-[#e88cab] hover:brightness-110 transition-all">
            Back to sign in
          </Link>
        </p>
      </motion.div>
    </div>
  )
}
