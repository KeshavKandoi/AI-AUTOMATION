import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { authApi } from '@/api/auth'
import { restoreSession } from '@/api/client'
import { useAuthStore } from '@/store/authStore'
import AuthShell from './AuthShell'

const loginSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(1, 'Password is required'),
})
type LoginForm = z.infer<typeof loginSchema>

export default function Login() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [serverError, setServerError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let active = true
    void restoreSession().then((token) => {
      if (active && token) navigate('/dashboard', { replace: true })
    })
    return () => { active = false }
  }, [navigate])

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) })

  const handleForgotPassword = () => {
    const email = getValues('email')
    navigate('/forgot-password', { state: email ? { email } : undefined })
  }

  const onSubmit = async (data: LoginForm) => {
    setServerError(null)
    setLoading(true)
    try {
      const res = await authApi.login(data)
      setAuth(res.data.user, res.data.access_token)
      navigate('/dashboard')
    } catch (err: any) {
      setServerError(
        err?.response?.data?.detail ?? 'Could not sign in. Check your details and try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell>
        <div className="mb-8">
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-signal)]">Welcome back</p>
          <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight text-[var(--color-text-primary)] sm:text-4xl">Sign in to WorkForge</h1>
          <p className="mt-3 text-sm leading-6 text-[var(--color-text-muted)]">Pick up where your work left off.</p>
        </div>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="flex flex-col gap-6 rounded-[1.75rem] border border-[var(--color-border)] bg-[var(--color-surface)]/75 p-7 shadow-xl shadow-black/10 sm:p-10"
        >
          {serverError && (
            <div role="alert" className="rounded-lg bg-[var(--color-alert-dim)] border border-[var(--color-alert)]/30 px-3 py-2 text-sm text-[var(--color-alert)]">
              {serverError}
            </div>
          )}

          <Input
            label="Email"
            leadingAdornment="✉️"
            type="email"
            placeholder="you@company.com"
            autoComplete="email"
            className="h-14 rounded-xl"
            error={errors.email?.message}
            {...register('email')}
          />
          <Input
            label="Password"
            leadingAdornment="🔒"
            type="password"
            placeholder="Enter your password"
            autoComplete="current-password"
            className="h-14 rounded-xl"
            error={errors.password?.message}
            {...register('password')}
          />

          <div className="flex justify-end text-sm">
            <button
              type="button"
              onClick={handleForgotPassword}
              className="text-[var(--color-signal)] hover:brightness-110 transition-all"
            >
              Forgot password?
            </button>
          </div>
          <Button type="submit" loading={loading} className="mt-1 h-14 w-full rounded-xl font-semibold">
            Sign in
          </Button>

        </form>

        <p className="mt-7 text-center text-sm text-[var(--color-text-muted)]">
          Don't have an account?{' '}
          <Link to="/signup" className="font-semibold text-[var(--color-signal)] hover:brightness-110 transition-all">
            Create an account
          </Link>
        </p>
    </AuthShell>
  )
}
