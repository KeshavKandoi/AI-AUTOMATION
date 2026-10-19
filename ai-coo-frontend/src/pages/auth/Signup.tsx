import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Building2, LockKeyhole, Mail, UserRound } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { authApi } from '@/api/auth'
import { restoreSession } from '@/api/client'
import AuthShell from './AuthShell'

const signupSchema = z.object({
  full_name: z.string().min(2, 'Enter your full name'),
  email: z.string().email('Enter a valid email'),
  organization_name: z.string().min(2, 'Enter your organization name'),
  password: z.string().min(8, 'At least 8 characters'),
})
type SignupForm = z.infer<typeof signupSchema>

export default function Signup() {
  const navigate = useNavigate()
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
    formState: { errors },
  } = useForm<SignupForm>({ resolver: zodResolver(signupSchema) })

  const onSubmit = async (data: SignupForm) => {
    setServerError(null)
    setLoading(true)
    try {
      const res = await authApi.signup(data)
      navigate('/verify-otp', { state: { email: res.data.email ?? data.email } })
    } catch (err: any) {
      setServerError(
        err?.response?.data?.detail ?? 'Could not create your account. Try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell>
        <div className="mb-8">
          <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight text-[var(--color-text-primary)] sm:text-4xl">Create your workspace</h1>
          <p className="mt-3 text-sm leading-6 text-[var(--color-text-muted)]">Set up your account, then choose the tools you want to connect.</p>
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
            label="Full name"
            leadingAdornment={<UserRound size={19} strokeWidth={1.8} />}
            placeholder="Your full name"
            autoComplete="name"
            className="h-14 rounded-xl"
            error={errors.full_name?.message}
            {...register('full_name')}
          />
          <Input
            label="Email"
            leadingAdornment={<Mail size={19} strokeWidth={1.8} />}
            type="email"
            placeholder="you@company.com"
            autoComplete="email"
            className="h-14 rounded-xl"
            error={errors.email?.message}
            {...register('email')}
          />
          <Input
            label="Organization name"
            leadingAdornment={<Building2 size={19} strokeWidth={1.8} />}
            placeholder="Your team or company"
            autoComplete="organization"
            className="h-14 rounded-xl"
            error={errors.organization_name?.message}
            {...register('organization_name')}
          />
          <Input
            label="Password"
            leadingAdornment={<LockKeyhole size={19} strokeWidth={1.8} />}
            type="password"
            placeholder="At least 8 characters"
            autoComplete="new-password"
            className="h-14 rounded-xl"
            error={errors.password?.message}
            {...register('password')}
          />

          <Button type="submit" loading={loading} className="mt-1 h-14 w-full rounded-xl font-semibold">
            Create account
          </Button>
        </form>

        <p className="mt-7 text-center text-sm text-[var(--color-text-muted)]">
          Already have an account?{' '}
          <Link to="/login" className="font-semibold text-[var(--color-signal)] hover:brightness-110 transition-all">
            Sign in
          </Link>
        </p>
    </AuthShell>
  )
}
