import { apiClient } from './client'
import type {
  LoginPayload,
  SignupPayload,
  VerifyOtpPayload,
  ForgotPasswordPayload,
  ResetPasswordPayload,
  ChangePasswordPayload,
  User,
} from '@/types/auth'


const authRequest = { baseURL: import.meta.env.PROD ? '/' : import.meta.env.VITE_API_BASE_URL, timeout: 30_000 }

let readyUntil = 0
let readinessCheck: Promise<void> | null = null

async function waitForBackend(): Promise<void> {
  if (!import.meta.env.PROD || Date.now() < readyUntil) return
  if (!readinessCheck) {
    readinessCheck = (async () => {
      const deadline = Date.now() + 100_000
      while (Date.now() < deadline) {
        try {
          const response = await fetch('/health', { cache: 'no-store', signal: AbortSignal.timeout(10_000) })
          if (response.ok && (await response.json()).status === 'ok') {
            readyUntil = Date.now() + 5 * 60_000
            return
          }
        } catch {
          // Render's free instance can return a loading page or a gateway error while waking.
        }
        await new Promise((resolve) => setTimeout(resolve, 3_000))
      }
      throw new Error('The sign-in service is still starting. Please try again in a minute.')
    })().finally(() => { readinessCheck = null })
  }
  return readinessCheck
}

async function postWhenReady<T>(path: string, payload: unknown) {
  await waitForBackend()
  return apiClient.post<T>(path, payload, authRequest)
}

export const authApi = {
  login: (payload: LoginPayload) =>
    postWhenReady<{ user: User; access_token: string }>('/auth/login', payload),

  signup: (payload: SignupPayload) =>
    postWhenReady<{ message: string; email: string }>('/auth/signup', payload),

  verifyOtp: (payload: VerifyOtpPayload) =>
    postWhenReady<{ user: User; access_token: string }>('/auth/verify-otp', payload),

  resendOtp: (email: string) =>
    postWhenReady<{ message: string }>('/auth/resend-otp', { email }),

  forgotPassword: (payload: ForgotPasswordPayload) =>
    postWhenReady<{ message: string }>('/auth/forgot-password', payload),

  resetPassword: (payload: ResetPasswordPayload) =>
    postWhenReady<{ message: string }>('/auth/reset-password', payload),

  resendResetOtp: (email: string) =>
    postWhenReady<{ message: string }>('/auth/resend-reset-otp', { email }),

  me: () => apiClient.get<User>('/auth/me', authRequest),

  changePassword: (payload: ChangePasswordPayload) =>
    apiClient.post<{ message: string }>('/auth/change-password', payload, authRequest),
  logout: () => apiClient.post('/auth/logout', {}, authRequest),
  deleteAccount: (password: string) =>
    apiClient.post<{ message: string }>('/account/delete', { password }),
}
