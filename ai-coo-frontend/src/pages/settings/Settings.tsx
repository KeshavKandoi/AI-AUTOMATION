import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  User as UserIcon,
  Mail,
  Building2,
  KeyRound,
  AlertCircle,
  CheckCircle2,
  Mail as MailIcon,
  Sun,
  Moon,
  Monitor,
  Bell,
  Smartphone,
  ShieldCheck,
  Trash2,
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { authApi } from '@/api/auth'
import Card from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { getStoredTheme, setStoredTheme, type ThemePreference } from '@/lib/theme'
import {
  getEmailNotificationsEnabled, setEmailNotificationsEnabled,
  getInAppNotificationsEnabled, setInAppNotificationsEnabled,
} from '@/lib/preferences'

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

const otpResetSchema = z
  .object({
    otp: z.string().length(6, 'Enter the 6-digit code'),
    new_password: z.string().min(8, 'At least 8 characters'),
    confirm_password: z.string().min(1, 'Please confirm your new password'),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords don't match",
    path: ['confirm_password'],
  })
type OtpResetForm = z.infer<typeof otpResetSchema>

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

function SectionHeader({ icon: Icon, title, tone }: { icon: typeof UserIcon; title: string; tone?: 'alert' }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <Icon size={16} className={tone === 'alert' ? 'text-[var(--color-alert)]' : 'text-[var(--color-text-muted)]'} />
      <h2 className={tone === 'alert' ? 'text-sm font-medium text-[var(--color-alert)]' : 'text-sm font-medium text-[var(--color-text-primary)]'}>
        {title}
      </h2>
    </div>
  )
}

function ToggleRow({
  icon: Icon, label, description, checked, onChange,
}: {
  icon: typeof UserIcon
  label: string
  description: string
  checked: boolean
  onChange: (checked: boolean) => void
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-3 border-b border-[var(--color-border)] last:border-b-0">
      <div className="flex items-start gap-3 min-w-0">
        <div className="h-9 w-9 rounded-lg bg-[var(--color-surface-hover)] flex items-center justify-center shrink-0">
          <Icon size={15} className="text-[var(--color-text-muted)]" />
        </div>
        <div className="min-w-0">
          <p className="text-sm text-[var(--color-text-primary)]">{label}</p>
          <p className="text-xs text-[var(--color-text-faint)] mt-0.5">{description}</p>
        </div>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={
          checked
            ? 'relative inline-flex h-6 w-11 items-center rounded-full bg-[var(--color-signal)] transition-colors shrink-0'
            : 'relative inline-flex h-6 w-11 items-center rounded-full bg-[var(--color-surface-hover)] border border-[var(--color-border)] transition-colors shrink-0'
        }
      >
        <span
          className={
            checked
              ? 'inline-block h-4 w-4 transform rounded-full bg-[var(--color-void)] transition-transform translate-x-6'
              : 'inline-block h-4 w-4 transform rounded-full bg-[var(--color-text-faint)] transition-transform translate-x-1'
          }
        />
      </button>
    </div>
  )
}

const THEME_OPTIONS: { value: ThemePreference; label: string; icon: typeof Sun }[] = [
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'system', label: 'System', icon: Monitor },
]

export default function Settings() {
  const user = useAuthStore((s) => s.user)
  const isDevAccount = useAuthStore((s) => s.isDevAccount)

  // --- Appearance ---
  const [theme, setTheme] = useState<ThemePreference>(() => getStoredTheme())
  const handleThemeChange = (pref: ThemePreference) => {
    setTheme(pref)
    setStoredTheme(pref)
  }

  // --- Notifications (device-local) ---
  const [emailNotifs, setEmailNotifs] = useState(() => getEmailNotificationsEnabled())
  const [inAppNotifs, setInAppNotifs] = useState(() => getInAppNotificationsEnabled())
  const handleEmailNotifsChange = (v: boolean) => {
    setEmailNotifs(v)
    setEmailNotificationsEnabled(v)
  }
  const handleInAppNotifsChange = (v: boolean) => {
    setInAppNotifs(v)
    setInAppNotificationsEnabled(v)
    // Reflect immediately without requiring a full reload — the sidebar
    // reads this via a plain function call on render, so a light nudge
    // (storage event doesn't fire in the same tab) isn't strictly needed
    // for correctness on next navigation, but a reload guarantees the
    // badge query re-evaluates right away.
  }

  // --- Security: change password (identical logic to Profile.tsx) ---
  const [mode, setMode] = useState<'password' | 'otp'>('password')
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

  const [otpSent, setOtpSent] = useState(false)
  const [otpSuccess, setOtpSuccess] = useState(false)
  const [cooldown, setCooldown] = useState(0)
  const {
    register: registerOtp,
    handleSubmit: handleOtpSubmit,
    reset: resetOtpForm,
    formState: { errors: otpErrors },
  } = useForm<OtpResetForm>({ resolver: zodResolver(otpResetSchema) })

  useEffect(() => {
    if (cooldown <= 0) return
    const t = setInterval(() => setCooldown((c) => c - 1), 1000)
    return () => clearInterval(t)
  }, [cooldown])

  const sendCodeMutation = useMutation({
    mutationFn: () => authApi.forgotPassword({ email: user!.email }),
    onSuccess: () => {
      setOtpSent(true)
      setCooldown(30)
    },
  })

  const resendCodeMutation = useMutation({
    mutationFn: () => authApi.resendResetOtp(user!.email),
    onSuccess: () => setCooldown(30),
  })

  const otpResetMutation = useMutation({
    mutationFn: (data: OtpResetForm) =>
      authApi.resetPassword({ email: user!.email, otp: data.otp, new_password: data.new_password }),
    onSuccess: () => {
      setOtpSuccess(true)
      resetOtpForm()
      setOtpSent(false)
      setTimeout(() => setOtpSuccess(false), 4000)
    },
  })

  const onSubmit = (data: ChangePasswordForm) => changePasswordMutation.mutate(data)
  const onOtpSubmit = (data: OtpResetForm) => otpResetMutation.mutate(data)

  return (
    <div className="p-6 md:p-8 max-w-3xl mx-auto flex flex-col gap-6">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
          Settings
        </h1>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          Manage your account, appearance, and preferences
        </p>
      </div>

      {/* Account Preferences */}
      <Card className="p-5">
        <SectionHeader icon={UserIcon} title="Account Preferences" />
        <InfoRow icon={UserIcon} label="Full name" value={user?.full_name || '—'} />
        <InfoRow icon={Mail} label="Email address" value={user?.email || '—'} />
        <InfoRow icon={Building2} label="Organization" value={user?.organization_name || '—'} />
        <p className="text-xs text-[var(--color-text-faint)] mt-3">
          To change your name or organization, visit your Profile page.
        </p>
      </Card>

      {/* Appearance */}
      <Card className="p-5">
        <SectionHeader icon={Sun} title="Appearance" />
        <p className="text-xs text-[var(--color-text-muted)] mb-3">
          Choose how AI COO looks on this device.
        </p>
        <div className="grid grid-cols-3 gap-2">
          {THEME_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => handleThemeChange(opt.value)}
              className={
                theme === opt.value
                  ? 'flex flex-col items-center gap-2 rounded-lg border border-[var(--color-signal)] bg-[var(--color-signal-dim)] px-3 py-4 text-[var(--color-signal)] transition-colors'
                  : 'flex flex-col items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-4 text-[var(--color-text-muted)] hover:border-[var(--color-border-hover)] transition-colors'
              }
            >
              <opt.icon size={18} />
              <span className="text-xs font-medium">{opt.label}</span>
            </button>
          ))}
        </div>
      </Card>

      {/* Notifications */}
      <Card className="p-5">
        <SectionHeader icon={Bell} title="Notifications" />
        <p className="text-xs text-[var(--color-text-muted)] mb-1">
          These preferences are saved on this device only — there's no synced notification backend yet.
        </p>
        <div className="mt-3">
          <ToggleRow
            icon={MailIcon}
            label="Email notifications"
            description="Receive account and activity emails."
            checked={emailNotifs}
            onChange={handleEmailNotifsChange}
          />
          <ToggleRow
            icon={Smartphone}
            label="In-app notifications"
            description="Show the unread badge and notification list in the sidebar."
            checked={inAppNotifs}
            onChange={handleInAppNotifsChange}
          />
        </div>
      </Card>

      {/* Security */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <KeyRound size={16} className="text-[var(--color-text-muted)]" />
            <h2 className="text-sm font-medium text-[var(--color-text-primary)]">Security</h2>
          </div>
          {!isDevAccount && (
            <div className="flex rounded-md border border-[var(--color-border)] overflow-hidden text-xs">
              <button
                type="button"
                onClick={() => setMode('password')}
                className={
                  mode === 'password'
                    ? 'px-2.5 py-1 bg-[var(--color-signal)] text-white'
                    : 'px-2.5 py-1 text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)]'
                }
              >
                Current password
              </button>
              <button
                type="button"
                onClick={() => setMode('otp')}
                className={
                  mode === 'otp'
                    ? 'px-2.5 py-1 bg-[var(--color-signal)] text-white'
                    : 'px-2.5 py-1 text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)]'
                }
              >
                Email code
              </button>
            </div>
          )}
        </div>

        {isDevAccount ? (
          <p className="text-xs text-[var(--color-text-faint)]">
            Password management isn't available for the dev account.
          </p>
        ) : mode === 'password' ? (
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
        ) : (
          <div className="flex flex-col gap-4">
            {otpSuccess && (
              <div className="flex items-center gap-2 rounded-lg bg-[var(--color-signal-dim)] border border-[var(--color-signal)]/30 px-3 py-2 text-xs text-[var(--color-signal)]">
                <CheckCircle2 size={14} />
                Password changed successfully.
              </div>
            )}

            {!otpSent ? (
              <>
                <p className="text-xs text-[var(--color-text-muted)] flex items-center gap-1.5">
                  <MailIcon size={13} />
                  We'll email a 6-digit code to <span className="text-[var(--color-text-primary)]">{user?.email}</span>
                </p>
                {sendCodeMutation.isError && (
                  <div className="flex items-start gap-2 rounded-lg bg-[var(--color-alert-dim)] border border-[var(--color-alert)]/30 px-3 py-2 text-xs text-[var(--color-alert)]">
                    <AlertCircle size={14} className="shrink-0 mt-0.5" />
                    Could not send the code. Please try again.
                  </div>
                )}
                <Button
                  type="button"
                  loading={sendCodeMutation.isPending}
                  onClick={() => sendCodeMutation.mutate()}
                  className="self-start"
                >
                  Send code
                </Button>
              </>
            ) : (
              <form onSubmit={handleOtpSubmit(onOtpSubmit)} className="flex flex-col gap-4">
                {otpResetMutation.isError && (
                  <div className="flex items-start gap-2 rounded-lg bg-[var(--color-alert-dim)] border border-[var(--color-alert)]/30 px-3 py-2 text-xs text-[var(--color-alert)]">
                    <AlertCircle size={14} className="shrink-0 mt-0.5" />
                    {(otpResetMutation.error as any)?.response?.data?.detail ?? 'Could not reset password. Check the code.'}
                  </div>
                )}

                <Input
                  label="Reset code"
                  placeholder="123456"
                  maxLength={6}
                  error={otpErrors.otp?.message}
                  {...registerOtp('otp')}
                />
                <Input
                  label="New password"
                  type="password"
                  placeholder="At least 8 characters"
                  error={otpErrors.new_password?.message}
                  {...registerOtp('new_password')}
                />
                <Input
                  label="Confirm new password"
                  type="password"
                  placeholder="Re-enter new password"
                  error={otpErrors.confirm_password?.message}
                  {...registerOtp('confirm_password')}
                />

                <div className="flex items-center gap-4">
                  <Button type="submit" loading={otpResetMutation.isPending}>
                    Change password
                  </Button>
                  <button
                    type="button"
                    onClick={() => resendCodeMutation.mutate()}
                    disabled={cooldown > 0 || resendCodeMutation.isPending}
                    className="text-xs text-[var(--color-signal)] hover:brightness-110 transition-all disabled:text-[var(--color-text-faint)] disabled:cursor-not-allowed"
                  >
                    {cooldown > 0 ? `Resend code in ${cooldown}s` : 'Resend code'}
                  </button>
                </div>
              </form>
            )}
          </div>
        )}
      </Card>

      {/* Privacy */}
      <Card className="p-5">
        <SectionHeader icon={ShieldCheck} title="Privacy" />
        <div className="flex flex-col gap-3 text-xs text-[var(--color-text-muted)] leading-relaxed">
          <p>
            Your data is scoped to your organization,{' '}
            <span className="text-[var(--color-text-primary)]">{user?.organization_name || 'your organization'}</span>.
            Tasks, memory, commit jobs, and connected integrations are only visible to members of this organization.
          </p>
          <p>
            Conversations, actions, and integration events are recorded in your organization's{' '}
            <span className="text-[var(--color-text-primary)]">Audit Logs</span>, which any member of your
            organization can review.
          </p>
          <p>
            Connected third-party tokens (e.g. GitHub) are stored encrypted and are only used to act on your
            behalf within AI COO.
          </p>
        </div>
      </Card>

      {/* Danger Zone */}
      <Card className="p-5 border-[var(--color-alert)]/30">
        <SectionHeader icon={Trash2} title="Danger Zone" tone="alert" />
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="text-sm text-[var(--color-text-primary)]">Delete account</p>
            <p className="text-xs text-[var(--color-text-faint)] mt-0.5 max-w-md">
              Account deletion isn't available yet — there's no backend endpoint to permanently and safely remove
              your account and organization data. Contact support if you need your account removed.
            </p>
          </div>
          <Button
            variant="secondary"
            disabled
            title="Account deletion isn't available yet"
            className="!border-[var(--color-alert)]/30 !text-[var(--color-alert)] opacity-50 cursor-not-allowed shrink-0"
          >
            <Trash2 size={14} />
            Delete account
          </Button>
        </div>
      </Card>
    </div>
  )
}
