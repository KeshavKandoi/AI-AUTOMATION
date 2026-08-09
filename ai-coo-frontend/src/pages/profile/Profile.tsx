import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { User as UserIcon, Mail, Building2, Calendar, KeyRound, AlertCircle, CheckCircle2 } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { authApi } from '@/api/auth'
import Card from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'

const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, 'Current password is required'),
    new_password: z.string().min(8, 'At least 8 characters'),
    confirm_password: z.string().min(1, 'Please confirm your new password'),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords don't match",
    path: ['confirm_password'],
  })
type ChangePasswordForm = z.infer<typeof changePasswordSchema>

function InfoRow({ icon: Icon, label, value }: { icon: typeof UserIcon; label: string; value: string }) {
  return (
    <div className="flex items-start gap-3 py-3 border-b border-[var(--color-border)] last:border-b-0">
      <div className="h-9 w-9 rounded-lg bg-[var(--color-surface-hover)] flex items-center justify-center shrink-0">
        <Icon size={15} className="text-[var(--color-text-muted)]" />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-[var(--color-text-faint)]">{label}</p>
        <p className="text-sm text-[var(--color-text-primary)] mt-0.5 break-words">{value}</p>
      </div>
    </div>
  )
}

export default function Profile() {
  const user = useAuthStore((s) => s.user)
  const isDevAccount = useAuthStore((s) => s.isDevAccount)
  const [success, setSuccess] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ChangePasswordForm>({ resolver: zodResolver(changePasswordSchema) })

  const changePasswordMutation = useMutation({
    mutationFn: (data: ChangePasswordForm) =>
      authApi.changePassword({ current_password: data.current_password, new_password: data.new_password }),
    onSuccess: () => {
      setSuccess(true)
      reset()
      setTimeout(() => setSuccess(false), 4000)
    },
  })

  const onSubmit = (data: ChangePasswordForm) => {
    changePasswordMutation.mutate(data)
  }

  const memberSince = user?.created_at
    ? new Date(user.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
    : '—'

  return (
    <div className="p-6 md:p-8 max-w-3xl mx-auto flex flex-col gap-6">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
          Profile
        </h1>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          Your account overview
        </p>
      </div>

      <Card className="p-5">
        <div className="flex items-center gap-3 mb-2">
          <div className="h-12 w-12 rounded-xl bg-[var(--color-signal-dim)] flex items-center justify-center shrink-0">
            <span className="text-base font-semibold text-[var(--color-signal)]">
              {(user?.full_name || user?.email || '?').charAt(0).toUpperCase()}
            </span>
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-[var(--color-text-primary)] truncate">
              {user?.full_name || 'Unnamed account'}
            </p>
            <p className="text-xs text-[var(--color-text-faint)] truncate">{user?.email}</p>
          </div>
        </div>

        <div className="mt-3">
          <InfoRow icon={UserIcon} label="Full name" value={user?.full_name || '—'} />
          <InfoRow icon={Mail} label="Email address" value={user?.email || '—'} />
          <InfoRow icon={Building2} label="Organization" value={user?.organization_name || '—'} />
          <InfoRow icon={Calendar} label="Member since" value={memberSince} />
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex items-center gap-2 mb-4">
          <KeyRound size={16} className="text-[var(--color-text-muted)]" />
          <h2 className="text-sm font-medium text-[var(--color-text-primary)]">Change password</h2>
        </div>

        {isDevAccount ? (
          <p className="text-xs text-[var(--color-text-faint)]">
            Password management isn't available for the dev account.
          </p>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
            {success && (
              <div className="flex items-center gap-2 rounded-lg bg-[var(--color-signal-dim)] border border-[var(--color-signal)]/30 px-3 py-2 text-xs text-[var(--color-signal)]">
                <CheckCircle2 size={14} />
                Password changed successfully.
              </div>
            )}
            {changePasswordMutation.isError && (
              <div className="flex items-start gap-2 rounded-lg bg-[var(--color-alert-dim)] border border-[var(--color-alert)]/30 px-3 py-2 text-xs text-[var(--color-alert)]">
                <AlertCircle size={14} className="shrink-0 mt-0.5" />
                {(changePasswordMutation.error as any)?.response?.data?.detail ?? 'Could not change password. Please try again.'}
              </div>
            )}

            <Input
              label="Current password"
              type="password"
              placeholder="••••••••"
              error={errors.current_password?.message}
              {...register('current_password')}
            />
            <Input
              label="New password"
              type="password"
              placeholder="At least 8 characters"
              error={errors.new_password?.message}
              {...register('new_password')}
            />
            <Input
              label="Confirm new password"
              type="password"
              placeholder="Re-enter new password"
              error={errors.confirm_password?.message}
              {...register('confirm_password')}
            />

            <Button type="submit" loading={changePasswordMutation.isPending} className="self-start">
              Change password
            </Button>
          </form>
        )}
      </Card>
    </div>
  )
}
