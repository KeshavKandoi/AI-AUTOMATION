import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { authApi } from '@/api/auth'

const schema = z.object({
  otp: z.string().length(6, 'Enter the 6-digit code'),
  new_password: z.string().min(8, 'At least 8 characters'),
})
type ResetForm = z.infer<typeof schema>

export default function ResetPassword() {
  const navigate = useNavigate()
  const location = useLocation()
  const email = (location.state as { email?: string })?.email ?? ''

  const [serverError, setServerError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetForm>({ resolver: zodResolver(schema) })

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
            Set a new password
          </h1>
          <p className="mt-1.5 text-sm text-[var(--color-text-muted)]">
            Enter the code sent to{' '}
            <span className="text-[var(--color-text-primary)] font-mono">{email || 'your email'}</span>
          </p>
        </div>

        {success ? (
          <div className="rounded-2xl border border-[var(--color-signal)]/30 bg-[var(--color-signal-dim)] p-6 text-center">
            <p className="text-sm text-[var(--color-signal)]">
              Password reset. Taking you to sign in…
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
              label="Reset code"
              placeholder="123456"
              maxLength={6}
              error={errors.otp?.message}
              {...register('otp')}
            />
            <Input
              label="New password"
              type="password"
              placeholder="At least 8 characters"
              error={errors.new_password?.message}
              {...register('new_password')}
            />

            <Button type="submit" loading={loading} className="w-full mt-1">
              Reset password
            </Button>
          </form>
        )}

        <p className="mt-6 text-center text-sm text-[var(--color-text-muted)]">
          <Link to="/login" className="text-[var(--color-signal)] hover:brightness-110 transition-all">
            Back to sign in
          </Link>
        </p>
      </motion.div>
    </div>
  )
}
