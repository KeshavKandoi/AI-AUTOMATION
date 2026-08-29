import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { authApi } from '@/api/auth'

const schema = z.object({ email: z.string().email('Enter a valid email') })
type ForgotForm = z.infer<typeof schema>

export default function ForgotPassword() {
  const navigate = useNavigate()
  const location = useLocation()
  // Arrives here already knowing the email (e.g. typed on the login page) --
  // in that case we skip asking again and send the reset code immediately.
  // Landing here directly (bookmark, typed URL) with no known email falls
  // back to the manual entry form below.
  const prefilledEmail = (location.state as { email?: string })?.email

  const [serverError, setServerError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [autoSending, setAutoSending] = useState(!!prefilledEmail)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotForm>({ resolver: zodResolver(schema) })

  const sendCode = async (email: string) => {
    setServerError(null)
    try {
      await authApi.forgotPassword({ email })
      navigate('/reset-password', { state: { email } })
    } catch (err: any) {
      setServerError(err?.response?.data?.detail ?? 'Could not send reset code.')
      setAutoSending(false)
    }
  }

  useEffect(() => {
    if (prefilledEmail) {
      sendCode(prefilledEmail)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const onSubmit = async (data: ForgotForm) => {
    setLoading(true)
    await sendCode(data.email)
    setLoading(false)
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
            Reset your password
          </h1>
          <p className="mt-1.5 text-sm text-[var(--color-text-muted)]">
            We'll email you a code to reset it
          </p>
        </div>

        {autoSending ? (
          <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60 backdrop-blur-xl p-6 text-center">
            <p className="text-sm text-[var(--color-text-muted)]">
              Sending a reset code to{' '}
              <span className="text-[var(--color-text-primary)] font-mono">{prefilledEmail}</span>…
            </p>
          </div>
        ) : (
          <form
            onSubmit={handleSubmit(onSubmit)}
            className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60 backdrop-blur-xl p-6 flex flex-col gap-4"
          >
            {serverError && (
              <div className="rounded-lg bg-[var(--color-alert-dim)] border border-[var(--color-alert)]/30 px-3 py-2 text-xs text-[var(--color-alert)]">
                {serverError}
              </div>
            )}

            <Input
              label="Email"
              type="email"
              placeholder="you@company.com"
              defaultValue={prefilledEmail}
              error={errors.email?.message}
              {...register('email')}
            />

            <Button type="submit" loading={loading} className="w-full mt-1">
              Send reset code
            </Button>
          </form>
        )}

        <p className="mt-6 text-center text-sm text-[var(--color-text-muted)]">
          Remembered it?{' '}
          <Link to="/login" className="text-[var(--color-signal)] hover:brightness-110 transition-all">
            Back to sign in
          </Link>
        </p>
      </motion.div>
    </div>
  )
}
